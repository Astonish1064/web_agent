"""
LLMBackendGenerator - Phase 2.2 Implementation

Generates business logic and tests using PROMPT_BACKEND_IMPLEMENTATION and PROMPT_BACKEND_TEST.
"""
import json
from typing import Dict

from ..interfaces import IBackendGenerator, ILLMProvider
from ..prompts.library import PROMPT_BACKEND_IMPLEMENTATION, PROMPT_BACKEND_TEST
from ..utils import clean_json_response, clean_code_response


class LLMBackendGenerator(IBackendGenerator):
    """Generates backend logic and tests using LLM."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
    
    def generate_logic(self, spec, instr_spec=None) -> str:
        """Generate business logic implementation."""
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
            {"name": getattr(i, 'name', ''), "parameters": getattr(i, 'parameters', []),
             "description": getattr(i, 'description', '')}
            for i in getattr(spec, 'interfaces', [])
        ])
        
        prompt = PROMPT_BACKEND_IMPLEMENTATION.format(
            website_seed=spec.seed,
            tasks_json=tasks_json,
            data_models_json=data_models_json,
            interfaces_json=interfaces_json
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_code_response(response)
    
    def generate_tests(self, spec, logic_code: str, generated_data: Dict) -> str:
        """Generate integration tests for the business logic."""
        tasks_json = json.dumps([
            {"id": getattr(t, 'id', ''), "description": getattr(t, 'description', '')}
            for t in getattr(spec, 'tasks', [])
        ])
        interfaces_json = json.dumps([
            {"name": getattr(i, 'name', '')}
            for i in getattr(spec, 'interfaces', [])
        ])
        
        prompt = PROMPT_BACKEND_TEST.format(
            website_seed=spec.seed,
            tasks_json=tasks_json,
            interfaces_json=interfaces_json,
            generated_data_json=json.dumps(generated_data)
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_code_response(response)
        
    def _parse_code_response(self, response: str) -> str:
        """Parse LLM response to extract code."""
        # Try as JSON first
        data = clean_json_response(response)
        if data and "code" in data:
            return data["code"]
        
        # If valid JSON parsing failed, try extracting code from potential invalid JSON
        cleaned_text = clean_code_response(response)
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
                                return raw_code
            except Exception:
                pass

        # Fallback: return the cleaned text itself (assuming it's raw code if not JSON object)
        return cleaned_text
