"""
Pipeline context management.
============================
Manages pipeline state and file I/O.
"""
import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from ..domain import WebsiteSpec, PageSpec, Task, Framework


@dataclass
class PipelineContext:
    """Holds all state during pipeline execution."""
    
    seed: str
    output_dir: str
    
    # Spec
    spec: Optional[WebsiteSpec] = None
    
    # Generated artifacts
    backend_code: str = ""
    evaluator_code: str = ""
    data: Optional[Dict] = None
    framework: Optional[Framework] = None
    generated_pages: Dict[str, str] = field(default_factory=dict)
    page_designs: Dict[str, Any] = field(default_factory=dict)
    task_plans: Dict[str, str] = field(default_factory=dict)
    verification_results: Optional[Dict] = None
    
    # Paths
    intermediates_dir: str = ""
    
    def __post_init__(self):
        """Initialize directories and spec."""
        # CRITICAL: Convert to absolute path to prevent path duplication issues
        # in subprocesses and validators
        self.output_dir = os.path.abspath(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.intermediates_dir = os.path.join(self.output_dir, "intermediates")
        os.makedirs(self.intermediates_dir, exist_ok=True)
        
        if self.spec is None:
            self.spec = WebsiteSpec(seed=self.seed)
    
    def save_file(self, filename: str, content: str) -> str:
        """Saves content to a file in output_dir."""
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path
    
    def load_file(self, filename: str) -> Optional[str]:
        """Loads content from a file in output_dir."""
        path = os.path.join(self.output_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return None
    
    def save_intermediate(self, filename: str, data: Any):
        """Saves intermediate data for debugging/resume."""
        path = os.path.join(self.intermediates_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, (dict, list)):
                json.dump(data, f, indent=2, default=lambda o: o.__dict__)
            elif hasattr(data, '__dict__'):
                json.dump(data.__dict__, f, indent=2, default=lambda o: o.__dict__)
            else:
                f.write(str(data))
    
    def load_intermediate(self, filename: str) -> Optional[Dict]:
        """Loads intermediate JSON data."""
        path = os.path.join(self.intermediates_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def is_planning_complete(self) -> bool:
        """Checks if planning phase has been completed."""
        return bool(
            self.spec and 
            self.spec.tasks and 
            self.spec.interfaces and 
            self.spec.pages
        )
    
    def restore(self):
        """Restores state from output_dir if exists."""
        from .config import IntermediateFiles, FileNames
        
        # 1. Restore Tasks
        tasks_data = self.load_intermediate(IntermediateFiles.TASKS)
        if tasks_data:
            self.spec.tasks = [Task(**t) for t in tasks_data]
            
        # 2. Restore Architecture (and Pages)
        arch_data = self.load_intermediate(IntermediateFiles.FINAL_ARCH)
        if arch_data:
            # Re-extract pages from architecture if needed
            if isinstance(arch_data, dict) and 'pages' in arch_data:
                from ..domain import PageSpec
                # Update spec pages if empty
                if not self.spec.pages:
                    self.spec.pages = [PageSpec.from_dict(p) for p in arch_data['pages']]
        
        # 3. Restore Interfaces
        iface_data = self.load_intermediate(IntermediateFiles.INTERFACES)
        if iface_data:
            from ..domain import InterfaceDef
            self.spec.interfaces = [InterfaceDef(**i) for i in iface_data]
            
        # 4. Restore Logic
        logic_code = self.load_file(FileNames.LOGIC)
        if logic_code:
            self.backend_code = logic_code
            
        # 5. Restore Generated Pages
        if self.spec.pages:
            # Try to load all generic HTML files
            for filename in os.listdir(self.output_dir):
                if filename.endswith(".html"):
                    content = self.load_file(filename)
                    if content:
                        self.generated_pages[filename] = content
        
        # 6. Restore Data
        data = self.load_intermediate(IntermediateFiles.GENERATED_DATA)
        if data:
            self.data = data
