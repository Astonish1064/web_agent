from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json

@dataclass
class Task:
    """Represents a generated user task (e.g., 'Buy a book')."""
    id: str
    name: str
    description: str
    steps: List[str]

    @staticmethod
    def from_dict(d):
        return Task(**d)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": self.steps
        }

@dataclass
class InterfaceDef:
    """Represents a Unified Interface signature."""
    name: str
    description: str
    parameters: List[Dict]
    returns: Dict
    related_tasks: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d):
        return InterfaceDef(**d)
    
    def to_dict(self):
        return self.__dict__

@dataclass
class DataModel:
    """Represents an entity in the system (e.g., Product)."""
    name: str
    attributes: Dict[str, str]  # name -> type

    @staticmethod
    def from_dict(d):
        return DataModel(**d)
    
    def to_dict(self):
        return self.__dict__

@dataclass
class VariableRequirement:
    """Defines a variable that must be set during execution for evaluation."""
    variable_name: str
    set_in_function: str
    set_condition: str

    @staticmethod
    def from_dict(d):
        return VariableRequirement(**d)
    
    def to_dict(self):
        return self.__dict__

@dataclass
class InstrumentationSpec:
    """
    The output of the 'Instrumentation Analysis Stage'.
    Defines where and what to instrument in the backend code.
    """
    requirements: List[VariableRequirement] = field(default_factory=list)
    
    @staticmethod
    def from_dict(d):
        return InstrumentationSpec(
            requirements=[VariableRequirement.from_dict(r) for r in d.get('requirements', [])]
        )
    
    def to_dict(self):
        return {"requirements": [r.to_dict() for r in self.requirements]}

@dataclass
class PageSpec:
    """Defines a single page within the website."""
    name: str # e.g. "Home", "Product Detail"
    filename: str # e.g. "index.html", "product.html"
    description: str
    required_interfaces: List[str] = field(default_factory=list) # IDs of interfaces this page uses

    @staticmethod
    def from_dict(d):
        valid_keys = {"name", "filename", "description", "required_interfaces"}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        if "description" not in filtered:
            filtered["description"] = ""
        return PageSpec(**filtered)
    
    def to_dict(self):
        return self.__dict__

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
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def from_dict(d):
        return WebsiteSpec(
            seed=d.get('seed', ''),
            tasks=[Task.from_dict(t) for t in d.get('tasks', [])],
            interfaces=[InterfaceDef.from_dict(i) for i in d.get('interfaces', [])],
            data_models=[DataModel.from_dict(m) for m in d.get('data_models', [])],
            pages=[PageSpec.from_dict(p) for p in d.get('pages', [])],
            task_instruction=d.get('task_instruction', '')
        )

    def to_dict(self) -> Dict:
        return {
            "seed": self.seed,
            "tasks": [t.to_dict() for t in self.tasks],
            "interfaces": [i.to_dict() for i in self.interfaces],
            "data_models": [m.to_dict() for m in self.data_models],
            "pages": [p.to_dict() for p in self.pages],
            "task_instruction": self.task_instruction
        }

@dataclass
class Framework:
    """Shared UI framework."""
    html: str
    css: str

    @staticmethod
    def from_dict(d):
        return Framework(**d)
    
    def to_dict(self):
        return self.__dict__

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
    generated_pages: Dict[str, str] = field(default_factory=dict) # filename -> content
    task_plans: Dict[str, str] = field(default_factory=dict) # task_id -> markdown_plan
    data: Optional[Dict] = None # Generated data as a dictionary
    framework: Optional[Framework] = None
