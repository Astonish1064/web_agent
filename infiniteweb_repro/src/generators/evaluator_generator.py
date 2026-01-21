"""
LLMEvaluatorGenerator - Phase 5 Implementation

Generates evaluator logic using PROMPT_INSTRUMENTATION_EVALUATOR.
"""
import json
from ..interfaces import IEvaluatorGenerator, ILLMProvider
from ..prompts.library import PROMPT_INSTRUMENTATION_EVALUATOR
from ..utils import clean_json_response

class LLMEvaluatorGenerator(IEvaluatorGenerator):
    """Generates evaluators using LLM."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
        
    def generate(self, spec, instr_spec, logic_code: str) -> str:
        """Generate evaluator script."""
        tasks_json = json.dumps([
            {"id": getattr(t, 'id', ''), "description": getattr(t, 'description', '')}
            for t in getattr(spec, 'tasks', [])
        ])
        
        # Create var_mapping from instr_spec
        var_mapping = []
        if instr_spec and hasattr(instr_spec, 'requirements'):
            for req in instr_spec.requirements:
                if req.get('needs_instrumentation'):
                    for var in req.get('required_variables', []):
                        var_mapping.append({
                            "task_id": req.get('task_id'),
                            "variable": var.get('variable_name')
                        })
                        
        prompt = PROMPT_INSTRUMENTATION_EVALUATOR.format(
            tasks_json=tasks_json,
            var_mapping_json=json.dumps(var_mapping),
            business_logic_code=logic_code,
            website_data_json="{}" # Can be enhanced
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_evaluator(response)
        
    def _parse_evaluator(self, response: str) -> str:
        data = clean_json_response(response)
        if not data:
            return "// Error parsing evaluator response"
            
        evals = data.get("evaluators", [])
        
        # Convert list of evaluator definitions to a JS script
        js_code = "class Evaluator {\n"
        js_code += "  constructor() { this.results = {}; }\n"
        js_code += "  async evaluate() {\n"
        
        for ev in evals:
            task_id = ev.get("task_id")
            logic = ev.get("evaluation_logic", "return false;")
            js_code += f"    // Evaluator for {task_id}\n"
            js_code += f"    try {{ {logic} }} catch(e) {{ console.error(e); }}\n"
        
        js_code += "    return this.results;\n"
        js_code += "  }\n}\n"
        return js_code
