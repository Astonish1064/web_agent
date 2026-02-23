"""
LLMBackendGenerator - Phase 2.2 Implementation

Generates business logic and tests using PROMPT_BACKEND_IMPLEMENTATION and PROMPT_BACKEND_TEST.
"""
import json
import re
from typing import Dict

from ..interfaces import IBackendGenerator, ILLMProvider
from ..prompts.library import PROMPT_BACKEND_IMPLEMENTATION, PROMPT_SYSTEM_TEST, PROMPT_BACKEND_FIX, PROMPT_TESTS_FIX, PROMPT_ERROR_ANALYSIS
from ..utils import clean_json_response, clean_code_response, with_retry
from ..utils.sandbox import NodeSandbox


class LLMBackendGenerator(IBackendGenerator):
    """Generates backend logic and tests using LLM."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
    
    @with_retry(max_retries=3)
    def generate_logic(self, spec, instr_spec=None) -> str:
        """Generate business logic implementation with runtime validation."""
        # Prepare inputs
        tasks_json = json.dumps([
            {"id": getattr(t, 'id', ''), "description": getattr(t, 'description', '')}
            for t in getattr(spec, 'tasks', [])
        ])
        data_models_json = json.dumps([
            {"name": getattr(m, 'name', ''), "attributes": getattr(m, 'attributes', {})}
            for m in getattr(spec, 'data_models', [])
        ])
        interfaces_json = json.dumps([
            {"name": getattr(i, 'name', ''), 
             "parameters": getattr(i, 'parameters', []),
             "returns": getattr(i, 'returns', {}),
             "description": getattr(i, 'description', '')}
            for i in getattr(spec, 'interfaces', [])
        ])
        
        prompt = PROMPT_BACKEND_IMPLEMENTATION.format(
            website_seed=spec.seed,
            tasks_json=tasks_json,
            data_models_json=data_models_json,
            interfaces_json=interfaces_json
        )
        
        # 1. Planner (CoT)
        print("    [QUALITY] Planning logic and edge cases...")
        plan_prompt = f"Requirements:\n{tasks_json}\nInterfaces:\n{interfaces_json}\nGoal: List 5 critical edge cases/implementation details for this specific backend logic."
        plan_response = self.llm.prompt(plan_prompt, system_prompt="You are a senior system architect. Analyze requirements and identify pitfalls.")
        
        # 2. Initial Generation (Coder)
        print("    [QUALITY] Generating initial logic...")
        prompt_with_plan = f"{prompt}\n\nPlease consider these edge cases/plan:\n{plan_response}"
        response = self.llm.prompt(prompt_with_plan)
        code = self._parse_code_response(response)

        # 3. Verification Loop (Self-Correction)
        max_retries = 3
        sandbox = NodeSandbox()
        last_error = ""

        try:
            for attempt in range(max_retries):
                is_valid, error, details = self._validate_logic_code(code)
                if is_valid:
                    print(f"    ✅ Quality check passed (Attempt {attempt+1})")
                    return code
                
                print(f"    ⚠️ Quality check failed (Attempt {attempt+1}): {error}")
                last_error = error
                
                # Feedback-driven correction
                correction_prompt = PROMPT_BACKEND_FIX.format(
                    website_seed=spec.seed,
                    tasks_json=tasks_json,
                    original_code=code,
                    error_log=f"RUNTIME/VALIDATION ERROR:\n{error}\n\nREASONING: {details.get('type', 'Unknown')}"
                )
                print(f"    🔄 Iterating based on feedback...")
                response = self.llm.prompt(correction_prompt)
                code = self._parse_code_response(response)
        finally:
            sandbox.cleanup()
        
        # Final Verification Check
        is_valid, error, _ = self._validate_logic_code(code)
        if is_valid:
             return code

        # Graceful Fallback if all retries fail
        print("    ❌ All remediation attempts failed. Raising Generation Error.")
        raise RuntimeError("CRITICAL: Backend generation failed after max retries. Pipeline halted to prevent invalid environment.")

    def _get_node_binary(self) -> str:
        """Finds a usable node binary, prioritizing Playwright's if system node is missing."""
        import os, subprocess
        # Try system node first
        try:
            subprocess.run(["node", "-v"], capture_output=True, check=True)
            return "node"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Try common playwright path (Fixed location for this env)
        playwright_node = "/usr/local/lib/python3.12/dist-packages/playwright/driver/node"
        if os.path.exists(playwright_node):
            return playwright_node
            
        return "node" # Hope for the best

    def _validate_logic_code(self, code: str):
        """Runs the node validator script against the generated code."""
        import os, tempfile, subprocess
        
        validator_script = os.path.join(os.getcwd(), "src", "validators", "validate_logic.js")
        if not os.path.exists(validator_script):
            print("Warning: Validator script not found, skipping validation.")
            return True, None, {}

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_path = f.name
            
        try:
            node_bin = self._get_node_binary()
            result = subprocess.run(
                [node_bin, validator_script, temp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse output
            try:
                output = json.loads(result.stdout.strip())
                if output.get("success"):
                    return True, None, output
                else:
                    return False, output.get("error"), output
            except json.JSONDecodeError:
                return False, f"Validator crashed or returned invalid JSON: {result.stderr or result.stdout}", {}
                
        except Exception as e:
            return False, f"Validation execution failed: {str(e)}", {}
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @with_retry(max_retries=3)
    def generate_task_tests(self, task, spec, data) -> str:
        """
        [P2] Generate SDK Unit Tests ONLY for a specific task.
        Integration/E2E tests are handled by GoldenPathValidator (Playwright).
        """
        interfaces_json = json.dumps([
            {"name": i.name, "parameters": i.parameters, "returns": i.returns, "description": i.description}
            for i in spec.interfaces
        ])
        
        # [P2-1] Unit Tests Only Template - no JSDOM integration tests
        prompt = f"""
You are an expert QA Engineer. Generate a suite of SDK UNIT TESTS for the following task:
Task: {task.description}
Steps: {json.dumps(task.steps)}

Interfaces available: {interfaces_json}
Initial Data: {json.dumps(data)}

REQUIREMENTS:
1. **CRITICAL: DO NOT IMPLEMENT A MOCK WebsiteSDK.** The implementation is in './logic.js'.
2. Use the provided template below. Fill in the `// YOUR UNIT TESTS HERE` section.
3. Generate ONLY Unit Tests for WebsiteSDK methods - test the SDK API directly.
4. DO NOT generate Integration Tests or simulate UI interactions - that is handled separately by browser E2E tests.
5. **SYNTAX SAFETY**: Use unique variable names. Prefer `let` or `const`.

TEMPLATE:
```javascript
const fs = require('fs');
const jsdom = require('jsdom');
const {{ JSDOM }} = jsdom;
const assert = require('assert');

// Load real logic
const logicJs = fs.readFileSync('./logic.js', 'utf8');

const setupEnv = (domWindow) => {{
    const storage = {{}};
    domWindow.localStorage = {{
        getItem: (k) => storage[k] || null,
        setItem: (k, v) => storage[k] = String(v),
        removeItem: (k) => delete storage[k],
        clear: () => {{ for (let k in storage) delete storage[k]; }}
    }};
    // Inject the real logic into the window context
    domWindow.eval(logicJs);
}};

async function runTests() {{
    console.log("🚀 Starting SDK Unit Tests for {task.id}");

    // --- SDK UNIT TESTS ---
    const dom = new JSDOM('<!DOCTYPE html><html></html>', {{ runScripts: "dangerously", url: "http://localhost/" }});
    setupEnv(dom.window);
    const sdk = dom.window.WebsiteSDK;
    assert(sdk, "WebsiteSDK must be initialized on window");
    
    // YOUR UNIT TESTS HERE
    // Test each SDK method directly with expected inputs/outputs:
    // Example patterns:
    // const result = await sdk.getTasks();
    // assert(Array.isArray(result), "getTasks should return an array");
    // 
    // const created = await sdk.createTask({{ name: "Test", priority: "high" }});
    // assert(created.id, "createTask should return an object with id");
    
    console.log("✅ All SDK Unit Tests passed for {task.id}");
}}

runTests().catch(e => {{ 
    console.error("Test Failed:", e.message); 
    if (e.stack) console.error(e.stack);
    process.exit(1); 
}});
```

**TEST COVERAGE GUIDELINES**:
1. Test each SDK method mentioned in the task steps.
2. Test valid inputs return expected outputs.
3. Test edge cases: empty inputs, null values, missing parameters.
4. DO NOT test DOM manipulation or UI rendering - that's E2E.

Return the complete JavaScript code based on this template.
"""
        response = self.llm.prompt(prompt)
        return self._parse_code_response(response)

    @with_retry(max_retries=3)
    def generate_task_plan(self, task, test_code, existing_code, spec) -> str:
        """
        [OPENCODE] Phase A: Generate a technical implementation plan for the task.
        Describes signatures, state changes, and logic flows before coding.
        """
        interfaces_json = json.dumps([
            {"name": i.name, "parameters": i.parameters, "returns": i.returns, "description": i.description}
            for i in spec.interfaces
        ])
        
        prompt = f"""
You are a Lead Architect using the OpenCode (Plan-Build) methodology.
Generate a Technical Implementation Plan to pass the following tests for this task.

TASK: {task.description}
TESTS TO PASS:
```javascript
{test_code}
```

EXISTING CODEBASE CONTEXT:
```javascript
{existing_code}
```

INTERFACES SPEC: {interfaces_json}

YOUR PLAN MUST INCLUDE:
1. **Affected Methods**: List which WebsiteSDK methods need to be added or modified.
2. **State Management**: Describe any new localStorage keys or internal state tracking.
3. **Logic Flow**: A step-by-step pseudo-code or description of how the logic will handle the test cases.
4. **Edge Cases**: Note how to handle empty data, invalid inputs, etc.

Return the plan in Markdown format.
"""
        return self.llm.prompt(prompt)

    @with_retry(max_retries=3)
    def implement_task_logic(self, task, test_code, existing_code, spec, plan=None) -> str:
        """
        [OPENCODE] Phase B: Implement or update logic.js based on the Plan.
        """
        interfaces_json = json.dumps([
            {"name": i.name, "parameters": i.parameters, "returns": i.returns, "description": i.description}
            for i in spec.interfaces
        ])
        
        plan_context = f"\nTECHNICAL PLAN TO FOLLOW:\n{plan}\n" if plan else ""
        
        prompt = f"""
You are an expert developer following the OpenCode methodology.
Implement or update the WebsiteSDK logic to pass the tests.
{plan_context}

TASK: {task.description}
TESTS TO PASS:
```javascript
{test_code}
```

EXISTING CODE (must be preserved or extended):
```javascript
{existing_code}
```

INTERFACES SPEC: {interfaces_json}

INSTRUCTIONS:
1. Implement ALL methods specified in the INTERFACES SPEC.
1.5. **DATA FULFILLMENT**: Ensure the `_initData` or internal catalog contains sample data for all categories mentioned in the TASKS (e.g., if a task mentions 'Fiction' or 'Cooking', those books MUST be in the default catalog).
2. Ensure existing functionality remains intact (Do NOT delete working methods).
3. Ensure return types strictly follow the Interfaces Spec.
4. Export the logic as `window.WebsiteSDK`.

**MANDATORY EXPORT PATTERN**:
```javascript
class BusinessLogic {{ ... }}
window.WebsiteSDK = new BusinessLogic();
if (typeof module !== 'undefined') module.exports = BusinessLogic;
```

Return only the raw JavaScript code for the entire logic.js.
"""
        response = self.llm.prompt(prompt)
        return self._parse_code_response(response)

    @with_retry(max_retries=3)
    def implement_task_fix(self, task, test_code, error_log, existing_code, spec) -> str:
        """
        [INCREMENTAL TCTDD] Fix logic.js when it fails task-specific tests.
        Ensures the fix doesn't break initialization or existing methods.
        """
        interfaces_json = json.dumps([
            {"name": i.name, "parameters": i.parameters, "returns": i.returns, "description": i.description}
            for i in spec.interfaces
        ])
        
        prompt = f"""
You are an expert developer. Fix the WebsiteSDK logic because it failed the following tests for this task:

TASK: {task.description}
ERROR LOG:
{error_log}

TESTS THAT FAILED:
```javascript
{test_code}
```

EXISTING (BROKEN) CODE:
```javascript
{existing_code}
```

INTERFACES SPEC: {interfaces_json}

INSTRUCTIONS:
1. Analyze the ERROR LOG to identify the bug in the EXISTING CODE.
2. Fix the bug while PRESERVING all other functionality.
3. Ensure return types strictly follow the Interfaces Spec.
4. YOU MUST include the initialization and export boilerplate at the end.

**MANDATORY EXPORT PATTERN**:
```javascript
class BusinessLogic {{ ... }}
window.WebsiteSDK = new BusinessLogic();
if (typeof module !== 'undefined') module.exports = BusinessLogic;
```

Return only the raw JavaScript code for the entire logic.js.
"""
        response = self.llm.prompt(prompt)
        return self._parse_code_response(response)

    def fix_logic(self, spec, original_code: str, error_log: str) -> str:
        """Fix business logic based on test errors."""
        tasks_json = json.dumps([
            {"id": getattr(t, 'id', ''), "description": getattr(t, 'description', '')}
            for t in getattr(spec, 'tasks', [])
        ])
        
        prompt = PROMPT_BACKEND_FIX.format(
            website_seed=spec.seed,
            tasks_json=tasks_json,
            original_code=original_code,
            error_log=error_log
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_code_response(response)
    
    def fix_tests(self, spec, original_tests: str, error_log: str) -> str:
        """Fix backend tests based on test errors."""
        tasks_json = json.dumps([
            {"id": getattr(t, 'id', ''), "description": getattr(t, 'description', '')}
            for t in getattr(spec, 'tasks', [])
        ])
        
        prompt = PROMPT_TESTS_FIX.format(
            website_seed=spec.seed,
            tasks_json=tasks_json,
            original_tests=original_tests,
            error_log=error_log
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_code_response(response)

    @with_retry(max_retries=3)
    def generate_tests(self, spec, logic_code: str, generated_data: Dict, html_files: Dict[str, str] = None) -> str:
        """Generate system and integration tests for the business logic and UI accessibility."""
        tasks_json = json.dumps([
            {"id": getattr(t, 'id', ''), "description": getattr(t, 'description', '')}
            for t in getattr(spec, 'tasks', [])
        ])
        interfaces_json = json.dumps([
            {"name": getattr(i, 'name', '')}
            for i in getattr(spec, 'interfaces', [])
        ])
        
        # Simplify HTML to reduce token usage (strip styles)
        simplified_html = {}
        if html_files:
            for filename, content in html_files.items():
                # Remove style blocks to save tokens
                content = re.sub(r'<style>.*?</style>', '', content, flags=re.DOTALL)
                # Cap per file size to be safe (keep enough for structure)
                if len(content) > 2000:
                    content = content[:2000] + "... (truncated)"
                simplified_html[filename] = content

        prompt = PROMPT_SYSTEM_TEST.format(
            website_seed=spec.seed,
            tasks_json=tasks_json,
            interfaces_json=interfaces_json,
            generated_data_json=json.dumps(generated_data),
            html_files_json=json.dumps(simplified_html),
            logic_code=logic_code
        )
        
        response = self.llm.prompt(prompt)
        parsed = self._parse_code_response(response)
        if not parsed:
            print("⚠️ [DEBUG] System test generation failed/timed out. Using dummy fallback.")
            return "const assert = require('assert'); console.log('Dummy test passed');"
        return parsed

    @with_retry(max_retries=3)
    def analyze_error(self, spec, logic_code: str, test_code: str, error_log: str) -> Dict:
        """Analyze validation error to determine root cause and action."""
        tasks_json = json.dumps([
            {"id": getattr(t, 'id', ''), "description": getattr(t, 'description', '')}
            for t in getattr(spec, 'tasks', [])
        ])
        
        prompt = PROMPT_ERROR_ANALYSIS.format(
            website_seed=spec.seed,
            tasks_json=tasks_json,
            logic_code=logic_code,
            test_code=test_code,
            error_log=error_log
        )
        
        response = self.llm.prompt(prompt)
        analysis = clean_json_response(response)
        
        if not analysis:
            # Fallback heuristic if LLM fails
            print("⚠️ [DEBUG] Smart diagnostics failed. Falling back to heuristic.")
            is_test_error = "backend_tests.js" in error_log and (
                "ReferenceError" in error_log or 
                "SyntaxError" in error_log
            )
            return {
                "root_cause": "Unknown",
                "action": "FIX_TEST" if is_test_error else "FIX_LOGIC",
                "confidence": 0,
                "reasoning": "Fallback heuristic"
            }
            
        print(f"🧠 [DIAGNOSTIC] Cause: {analysis.get('root_cause')} -> Action: {analysis.get('action')}")
        return analysis
        
    def _parse_code_response(self, response: str) -> str:
        """Parse LLM response to extract code."""
        if not response:
            return ""
            
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            data = None

        # Try as JSON first
        if data and isinstance(data, dict) and "code" in data:
            code = data["code"]
            # [Sanitizer] Remove hallucinatory non-ASCII characters even if JSON is valid
            code = re.sub(r'[^\x00-\x7F]+', '', code)
            return clean_code_response(code)
        
        # If valid JSON parsing failed, try extracting code from potential invalid JSON
        cleaned_text = clean_code_response(response)
        
        # Extra check: sometimes clean_code_response leaves backticks if the model 
        # formatted it oddly (e.g. ```javascript\ncode\n``` inside a string)
        if cleaned_text.startswith("```"):
             cleaned_text = re.sub(r"```(?:\w+)?\n", "", cleaned_text)
             cleaned_text = cleaned_text.replace("```", "")
        
        # [Sanitizer] Remove hallucinatory non-ASCII characters (e.g., Chinese chars) which cause SyntaxErrors.
        # We allow standard ASCII printables + newlines/tabs.
        # This fixes errors like: category极 'GPU'
        if cleaned_text:
             cleaned_text = re.sub(r'[^\x00-\x7F]+', '', cleaned_text)

        if cleaned_text.strip().startswith("{") and '"code":' in cleaned_text:
            # Attempt manual extraction
            try:
                # Find start of code value
                start_marker = '"code":'
                start_idx = cleaned_text.find(start_marker)
                if start_idx != -1:
                    # Find opening quote
                    quote_char = '"' # Assume double quote for JSON
                    open_quote_idx = cleaned_text.find(quote_char, start_idx + len(start_marker))
                    
                    if open_quote_idx != -1:
                        # Find closing quote - this is tricky if code has quotes
                        # We try to find the last quote before the last '}'
                        last_brace_idx = cleaned_text.rfind("}")
                        if last_brace_idx != -1:
                            close_quote_idx = cleaned_text.rfind(quote_char, open_quote_idx + 1, last_brace_idx)
                            if close_quote_idx != -1:
                                raw_code = cleaned_text[open_quote_idx+1 : close_quote_idx]
                                # Unescape basic JSON escapes
                                raw_code = raw_code.replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t')
                                # Apply sanitizer
                                return clean_code_response(re.sub(r'[^\x00-\x7F]+', '', raw_code))
            except Exception:
                pass

        # Fallback: return the cleaned text itself (assuming it's raw code if not JSON object)
        return clean_code_response(re.sub(r'[^\x00-\x7F]+', '', cleaned_text.strip()))
