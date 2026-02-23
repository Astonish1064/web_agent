"""
IntegrationFixer - Phase 3 (Healing) Implementation

Uses LLM to analyze integration errors (e.g., frontend calling undefined backend functions)
and patches the frontend code.
"""
import os
import json
import re
from typing import Dict, List, Tuple
from ..interfaces import ILLMProvider
from ..utils import clean_code_response


class RootCauseClassifier:
    """
    Analyzes integration errors to determine the root cause layer.
    Routes errors to the correct fixer instead of blindly patching HTML.
    """
    
    # Error category constants
    FILE_MISSING = "FILE_MISSING"
    SERVER_ERROR = "SERVER_ERROR"
    BACKEND_EXPORT_MISSING = "BACKEND_EXPORT_MISSING"
    FRONTEND_CODE_ERROR = "FRONTEND_CODE_ERROR"
    SCRIPT_EXECUTION_ERROR = "SCRIPT_EXECUTION_ERROR"
    
    def classify(self, errors: List[str], output_dir: str) -> Dict[str, str]:
        """
        Classify each error into a root cause category.
        Returns a dict mapping error_message -> category.
        """
        classifications = {}
        
        for error in errors:
            # Check for 404/file not found errors
            if "404" in error or "File not found" in error:
                # Determine which file is missing
                if "logic.js" in error:
                    logic_path = os.path.join(output_dir, "logic.js")
                    if not os.path.exists(logic_path):
                        classifications[error] = self.FILE_MISSING
                    else:
                        classifications[error] = self.SERVER_ERROR
                else:
                    classifications[error] = self.SERVER_ERROR
            
            # Check for SDK not defined errors
            elif "WebsiteSDK not defined" in error or "WebsiteSDK is not defined" in error:
                logic_path = os.path.join(output_dir, "logic.js")
                if os.path.exists(logic_path):
                    with open(logic_path, 'r') as f:
                        content = f.read()
                    if "window.WebsiteSDK" not in content:
                        classifications[error] = self.BACKEND_EXPORT_MISSING
                    else:
                        # Export exists but SDK still undefined - execution issue
                        classifications[error] = self.SCRIPT_EXECUTION_ERROR
                else:
                    classifications[error] = self.FILE_MISSING
            
            # Check for function call errors (typical frontend issues)
            elif "TypeError" in error or "is not a function" in error:
                classifications[error] = self.FRONTEND_CODE_ERROR
            
            # Check for JSON parse errors
            elif "not valid JSON" in error:
                classifications[error] = self.FRONTEND_CODE_ERROR
            
            # Default to frontend code error
            else:
                classifications[error] = self.FRONTEND_CODE_ERROR
        
        return classifications
    
    def get_summary(self, classifications: Dict[str, str]) -> Dict[str, int]:
        """Returns count of errors per category."""
        summary = {}
        for category in classifications.values():
            summary[category] = summary.get(category, 0) + 1
        return summary
    
    def should_fix_backend(self, classifications: Dict[str, str]) -> bool:
        """Returns True if any error requires backend fix."""
        return any(
            cat in [self.BACKEND_EXPORT_MISSING, self.FILE_MISSING, self.SCRIPT_EXECUTION_ERROR]
            for cat in classifications.values()
        )
    
    def should_fix_frontend(self, classifications: Dict[str, str]) -> bool:
        """Returns True if any error requires frontend fix."""
        return self.FRONTEND_CODE_ERROR in classifications.values()


class BackendFixer:
    """
    Fixes backend logic.js issues that IntegrationFixer cannot handle.
    Includes: SDK export injection, runtime error fixing, styles.css generation.
    """
    
    def __init__(self, llm: ILLMProvider = None):
        self.llm = llm
    
    def fix_sdk_export(self, logic_path: str) -> bool:
        """
        Ensure WebsiteSDK is properly exported to window.
        Returns True if fix was applied, False if already correct.
        """
        if not os.path.exists(logic_path):
            print(f"   ❌ BackendFixer: {logic_path} not found")
            return False
        
        with open(logic_path, 'r') as f:
            code = f.read()
        
        # Check if export exists
        if 'window.WebsiteSDK' in code:
            return False  # Already exported
        
        # Find class name
        match = re.search(r'class\s+(\w+)\s*\{', code)
        if match:
            class_name = match.group(1)
            export_code = f"\n// Auto-injected SDK export by BackendFixer\nif (typeof window !== 'undefined') {{\n  window.WebsiteSDK = new {class_name}();\n}}\n"
            code += export_code
            with open(logic_path, 'w') as f:
                f.write(code)
            print(f"   ✓ BackendFixer: Injected SDK export for class '{class_name}'")
            return True
        
        print("   ❌ BackendFixer: Could not find class name in logic.js")
        return False
    
    def validate_and_fix_runtime_errors(self, logic_path: str) -> Tuple[bool, str]:
        """
        Run logic.js through Node.js to detect and report runtime errors.
        Returns (success, error_message).
        """
        import subprocess
        import shutil
        
        if not os.path.exists(logic_path):
            return False, "File not found"
        
        # Find node binary (try system node first, then Playwright's bundled node)
        node_binary = shutil.which("node")
        if not node_binary:
            # Try Playwright's bundled node
            import playwright
            pw_path = os.path.dirname(playwright.__file__)
            candidates = [
                os.path.join(pw_path, "driver", "node"),
                os.path.join(pw_path, "driver", "node.exe"),
            ]
            for candidate in candidates:
                if os.path.exists(candidate):
                    node_binary = candidate
                    break
        
        if not node_binary:
            return False, "Node.js not found (neither system node nor Playwright bundled)"
        
        # Create a test wrapper script
        test_script = """
const fs = require('fs');
const path = require('path');

// Mock browser globals for Node.js
global.window = global;
global.document = { 
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: () => {}
};
global.localStorage = {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
    clear: () => {}
};

try {
    require('%s');
    
    // Check if WebsiteSDK is defined
    if (typeof global.WebsiteSDK === 'undefined') {
        console.error('RUNTIME_ERROR: WebsiteSDK is not defined after loading logic.js');
        process.exit(1);
    }
    
    console.log('OK: logic.js loaded successfully, WebsiteSDK defined');
    process.exit(0);
} catch (e) {
    console.error('RUNTIME_ERROR: ' + e.message);
    console.error('STACK: ' + e.stack);
    process.exit(1);
}
""" % logic_path.replace('\\', '/')
        
        # Write test script
        test_script_path = os.path.join(os.path.dirname(logic_path), '_backend_test.js')
        with open(test_script_path, 'w') as f:
            f.write(test_script)
        
        try:
            result = subprocess.run(
                [node_binary, test_script_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr or result.stdout
        except subprocess.TimeoutExpired:
            return False, "Node.js execution timed out"
        except Exception as e:
            return False, str(e)
        finally:
            # Cleanup
            if os.path.exists(test_script_path):
                os.remove(test_script_path)
    
    def ensure_styles_css(self, output_dir: str) -> bool:
        """
        Ensure styles.css exists. If not, create a minimal placeholder.
        Returns True if file was created.
        """
        styles_path = os.path.join(output_dir, 'styles.css')
        
        if os.path.exists(styles_path):
            return False
        
        # Create minimal CSS
        minimal_css = """/* Auto-generated placeholder styles.css by BackendFixer */
:root {
    --primary-color: #2563eb;
    --background-color: #0a0e17;
    --text-color: #f8fafc;
    --border-color: #1e293b;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: var(--background-color);
    color: var(--text-color);
    min-height: 100vh;
}
"""
        with open(styles_path, 'w') as f:
            f.write(minimal_css)
        
        print(f"   ✓ BackendFixer: Created placeholder styles.css")
        return True
    
    def fix_all(self, output_dir: str) -> Dict[str, bool]:
        """
        Run all backend fixes and return results.
        """
        results = {}
        logic_path = os.path.join(output_dir, 'logic.js')
        
        # 1. Ensure styles.css exists
        results['styles_css'] = self.ensure_styles_css(output_dir)
        
        # 2. Fix SDK export
        results['sdk_export'] = self.fix_sdk_export(logic_path)
        
        # 3. Validate runtime
        success, error = self.validate_and_fix_runtime_errors(logic_path)
        results['runtime_valid'] = success
        if not success:
            print(f"   ⚠️ BackendFixer: Runtime validation failed: {error[:200]}")
        
        return results


from typing import Tuple

PROMPT_INTEGRATION_FIX = """
You are a Senior Frontend Integration Engineer.
Your job is to fix Frontend (HTML/JS) code that is failing to integrate with the Backend (WebsiteSDK).

CONTEXT:
1. Valid Backend Signatures (What is actually available in logic.js):
   {backend_signatures}

2. Integration Errors (What went wrong):
   {error_logs}

3. Current Frontend Code (The failing file):
   {frontend_code}

INSTRUCTIONS:
1. Analyze the errors. Most likely, the frontend is calling a function that DOES NOT EXIST in the backend.
2. Fix the frontend code to:
   - Use ONLY the functions listed in "Valid Backend Signatures".
   - If a function is missing, REMOVE the call or the UI element triggering it.
   - **CRITICAL NEGATIVE CONSTRAINTS**:
     - Do NOT mock functions (no `alert` or `console.log` stubs).
     - Do NOT inject new `<script>` blocks or inline JS headers.
     - Do NOT define global helper functions.
3. Return ONLY the fixed HTML/JS code.

Return JSON format:
{{"code": "Complete fixed HTML string"}}
"""

class IntegrationFixer:
    """Fixes integration errors between Frontend and Backend."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm

    def fix_frontend_integration(self, 
                               frontend_code: str, 
                               backend_code: str, 
                               error_logs: List[str]) -> str:
        """
        Analyzes errors and backend code to patch frontend code.
        """
        
        # 1. Extract backend signatures (naive regex)
        # We want to show the model what functions actually exist
        signatures = self._extract_backend_signatures(backend_code)
        
        # 2. Construct Prompt
        prompt = PROMPT_INTEGRATION_FIX.format(
            backend_signatures=json.dumps(signatures, indent=2),
            error_logs="\n".join(error_logs),
            frontend_code=frontend_code[:12000] # Fit in context
        )
        
        # 3. Call LLM
        print(f"    🔧 IntegrationFixer: Attemping to fix {len(error_logs)} errors...")
        response = self.llm.prompt(prompt)
        
        # 4. Parse response
        fixed_code = self._parse_code_response(response)
        
        if not fixed_code or len(fixed_code) < 100:
            print("    ⚠️ IntegrationFixer failed to produce valid code. Keeping original.")
            return frontend_code
            
        print("    ✅ IntegrationFixer generated a patch.")
        return fixed_code

    def _extract_backend_signatures(self, backend_code: str) -> List[str]:
        """
        Extracts function names from 'class BusinessLogic { ... }'
        Simple regex heuristic.
        """
        matches = re.findall(r'(\w+)\s*\(.*?\)\s*\{', backend_code)
        # Filter out constructor, strict private members if needed
        # But keeping _helpers is fine for context, though frontend shouldn't call them
        valid = [m for m in matches if m not in ['constructor', 'if', 'for', 'while', 'switch', 'catch']]
        return valid

    def _parse_code_response(self, response: str) -> str:
        """Parse LLM response to extract code."""
        if not response:
            return ""
        try:
            data = json.loads(response)
            if "code" in data:
                return clean_code_response(data["code"])
        except:
            pass
        return clean_code_response(response)
