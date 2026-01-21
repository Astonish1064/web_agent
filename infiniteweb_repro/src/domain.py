from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json

@dataclass
class Task:
    """Represents a generated user task (e.g., 'Buy a book')."""
    id: str
    description: str
    complexity: int
    required_steps: List[str]

@dataclass
class InterfaceDef:
    """Represents a Unified Interface signature."""
    name: str
    parameters: Dict[str, str]  # name -> type
    return_type: str
    description: str

@dataclass
class DataModel:
    """Represents an entity in the system (e.g., Product)."""
    name: str
    attributes: Dict[str, str]  # name -> type

@dataclass
class VariableRequirement:
    """Defines a variable that must be set during execution for evaluation."""
    variable_name: str
    set_in_function: str
    set_condition: str

@dataclass
class InstrumentationSpec:
    """
    The output of the 'Instrumentation Analysis Stage'.
    Defines where and what to instrument in the backend code.
    """
    requirements: List[VariableRequirement] = field(default_factory=list)

@dataclass
class PageSpec:
    """Defines a single page within the website."""
    name: str # e.g. "Home", "Product Detail"
    filename: str # e.g. "index.html", "product.html"
    description: str
    required_interfaces: List[str] = field(default_factory=list) # IDs of interfaces this page uses

@dataclass
class WebsiteSpec:
    """
    The output of the 'Unified Specification Stage'.
    Contains all shared definitions for the website.
    """
    seed: str
    tasks: List[Task] = field(default_factory=list)
    interfaces: List[InterfaceDef] = field(default_factory=list)
    data_models: List[DataModel] = field(default_factory=list)
    pages: List[PageSpec] = field(default_factory=list) # NEW: Multi-page support
    task_instruction: str = "" # The primary instruction to display to the user/agent


    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, indent=2)

@dataclass
class GenerationContext:
    """
    Holds the state of the generation pipeline.
    Passed between stages.
    """
    seed: str
    spec: Optional[WebsiteSpec] = None
    instr_spec: Optional[InstrumentationSpec] = None # NEW
    backend_code: Optional[str] = None  # logic.js
    frontend_code: Optional[str] = None # index.html
    evaluator_code: Optional[str] = None # evaluator.js
    output_dir: str = ""
