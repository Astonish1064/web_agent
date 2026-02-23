"""
LLMDataGenerator - Phase 2.1 Implementation

Generates realistic website data using PROMPT_DATA_GENERATION.
"""
import json
from typing import Dict

from ..interfaces import IDataGenerator, ILLMProvider
from ..prompts.library import PROMPT_DATA_GENERATION
from ..utils import clean_json_response, with_retry

class LLMDataGenerator(IDataGenerator):
    """Generates website data using LLM."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
    
    @with_retry(max_retries=3)
    def generate(self, spec) -> Dict:
        """Generate static data for the website."""
        # Prepare inputs
        tasks_json = json.dumps([
            {"id": getattr(t, 'id', ''), "description": getattr(t, 'description', '')}
            for t in getattr(spec, 'tasks', [])
        ])
        
        data_types_info = []
        for model in getattr(spec, 'data_models', []):
            data_types_info.append({
                "data_type_name": getattr(model, 'name', '').lower() + "s",  # pluralize
                "fields": getattr(model, 'attributes', {}),
                "generation_type": "many",
                "max_items": 20
            })
        
        prompt = PROMPT_DATA_GENERATION.format(
            website_seed=spec.seed,
            tasks_json=tasks_json,
            data_types_info_json=json.dumps(data_types_info)
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_response(response)
    
    def _parse_response(self, response: str) -> Dict:
        """Parse LLM response into data dict."""
        data = clean_json_response(response)
        if not data:
            error_msg = f"Data Gen Parsing Failed. Full Response length: {len(response)}. Response: {response}"
            print(error_msg)
            raise ValueError(error_msg)
        return data.get("static_data", {})
