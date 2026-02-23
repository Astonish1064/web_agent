"""
LLMInstrumentationGenerator - Phase 5 Implementation

Analyzes logic and injects instrumentation using official prompts.
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict

from ..interfaces import IInstrumentationGenerator, ILLMProvider
from ..prompts.library import PROMPT_INSTRUMENTATION_ANALYSIS, PROMPT_INSTRUMENTATION_CODE
from ..domain import InstrumentationSpec
from ..utils import clean_json_response, clean_code_response, with_retry

@dataclass
class InstrumentationRequirements:
    """Output of analysis."""
    requirements: List[Dict] = field(default_factory=list)


class LLMInstrumentationGenerator(IInstrumentationGenerator):
    """Generates instrumentation using LLM."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
        
    @with_retry(max_retries=3)
    def analyze(self, spec, logic_code: str) -> InstrumentationRequirements:
        """Analyze logic to determine instrumentation needs."""
        # Convert tasks to simple list for prompt
        tasks_simpl = [{"id": getattr(t, 'id', ''), "description": getattr(t, 'description', '')} 
                      for t in getattr(spec, 'tasks', [])]
        
        prompt = PROMPT_INSTRUMENTATION_ANALYSIS.format(
            tasks_json=json.dumps(tasks_simpl),
            code_snippet=logic_code,
            existing_storage_vars_json="[]", # Can be enhanced to parse actual use
            storage_keys_json="[]"
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_analysis(response)
        
    def _parse_analysis(self, response: str) -> InstrumentationRequirements:
        data = clean_json_response(response)
        if not data:
            return InstrumentationRequirements()
        return InstrumentationRequirements(requirements=data.get("requirements", []))
            
    @with_retry(max_retries=3)
    def inject(self, logic_code: str, instr_spec) -> str:
        """Inject instrumentation code."""
        reqs = getattr(instr_spec, 'requirements', [])
        if not reqs:
            return logic_code
            
        prompt = PROMPT_INSTRUMENTATION_CODE.format(
            original_code=logic_code,
            instrumentation_specs_json=json.dumps(reqs)
        )
        
        # This prompt asks to return the CODE directly (or maybe implicitly).
        # We assume result is code. The implementation in prompt says "Return: Complete instrumented... code"
        response = self.llm.prompt(prompt)
        return clean_code_response(response)

    def generate_spec(self, spec) -> InstrumentationSpec:
        """Legacy compatibility."""
        return InstrumentationSpec(metrics={})
