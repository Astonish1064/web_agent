"""
LLMInterfaceDesigner - Phase 1.2 Implementation

Designs API interfaces using PROMPT_INTERFACE_DESIGN and PROMPT_INTERFACE_WRAPPING.
"""
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple

from ..interfaces import IInterfaceDesigner, ILLMProvider
from ..prompts.library import PROMPT_INTERFACE_DESIGN, PROMPT_INTERFACE_WRAPPING
from ..utils import clean_json_response, with_retry
from ..validation import SchemaValidator

from ..domain import InterfaceDef


@dataclass
class HelperFunction:
    """A helper function definition."""
    name: str
    description: str
    visibility: str = "private"

@dataclass
class WrappedInterfaces:
    """Result of interface wrapping."""
    wrapped_interfaces: List[InterfaceDef]
    state_data_models: List[Dict]
    implementation_mapping: List[Dict]

class LLMInterfaceDesigner(IInterfaceDesigner):
    """Designs interfaces using LLM with official prompts."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
    
    def design(self, spec) -> List[InterfaceDef]:
        """Design interfaces for the website."""
        result = self.design_with_helpers(spec)
        if not result:
            return []
            
        interfaces, _ = result
        return interfaces
    
    @with_retry(max_retries=3)
    def design_with_helpers(self, spec) -> Tuple[List[InterfaceDef], List[HelperFunction]]:
        """Design interfaces and return helper functions too."""
        # Prepare inputs
        tasks_json = json.dumps([
            {"id": getattr(t, 'id', 'unknown'), 
             "description": getattr(t, 'description', '')}
            for t in spec.tasks
        ])
        data_models_json = json.dumps([
            {"name": getattr(m, 'name', ''), 
             "attributes": getattr(m, 'attributes', {})}
            for m in spec.data_models
        ])
        pages_info = json.dumps([
            {"name": getattr(p, 'name', ''), 
             "filename": getattr(p, 'filename', '')}
            for p in spec.pages
        ])
        
        prompt = PROMPT_INTERFACE_DESIGN.format(
            website_seed=spec.seed,
            tasks_json=tasks_json,
            data_models_json=data_models_json,
            pages_info=pages_info
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_design_response(response)
    
    def _parse_design_response(self, response: str) -> Tuple[List[InterfaceDef], List[HelperFunction]]:
        """Parse LLM response into InterfaceDef and HelperFunction objects."""
        data = clean_json_response(response)
        if not data:
            print(f"Interface Design Parsing Failed. Response: {response[:100]}...")
            return [], []
        
        interfaces_data = data.get("interfaces", [])
        
        # Robustness: Validate Schema
        if not SchemaValidator.validate_interfaces(interfaces_data):
            print(f"Interface Verification Failed. Structure invalid.")
            return [], []
        
        interfaces = []
        for iface_data in interfaces_data:
            interfaces.append(self._sanitize_interface(iface_data))
        
        helpers = []
        for helper_data in data.get("helperFunctions", []):
            helpers.append(HelperFunction(
                name=helper_data.get("name", "_unknown"),
                description=helper_data.get("description", ""),
                visibility=helper_data.get("visibility", "private")
            ))
        
        return interfaces, helpers
    
    def _sanitize_interface(self, data: dict) -> InterfaceDef:
        """Sanitize interface data."""
        return InterfaceDef(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            parameters=data.get("parameters", []),
            returns=data.get("returns", {}),
            related_tasks=data.get("relatedTasks", [])
        )
    
    def wrap(self, interfaces: List, data_models: List) -> WrappedInterfaces:
        """Wrap interfaces to hide system-managed parameters."""
        interfaces_json = json.dumps([
            {"name": getattr(i, 'name', ''), 
             "parameters": getattr(i, 'parameters', [])}
            for i in interfaces
        ])
        data_models_json = json.dumps([
            {"name": getattr(m, 'name', ''), 
             "attributes": getattr(m, 'attributes', {})}
            for m in data_models
        ])
        
        prompt = PROMPT_INTERFACE_WRAPPING.format(
            website_type="generic",
            original_interfaces_json=interfaces_json,
            data_models_json=data_models_json
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_wrap_response(response)
    
    def _parse_wrap_response(self, response: str) -> WrappedInterfaces:
        """Parse wrap response."""
        data = clean_json_response(response)
        if not data:
             return WrappedInterfaces([], [], [])
        
        wrapped = []
        for iface_data in data.get("wrapped_interfaces", []):
            wrapped.append(self._sanitize_interface(iface_data))
        
        return WrappedInterfaces(
            wrapped_interfaces=wrapped,
            state_data_models=data.get("state_data_models", []),
            implementation_mapping=data.get("implementation_mapping", [])
        )
