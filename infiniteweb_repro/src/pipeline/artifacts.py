"""
Artifact management for pipeline intermediates.
================================================
Handles saving and loading of intermediate files.
"""
import os
import json
from typing import Any, Optional, List
from .config import IntermediateFiles


class ArtifactManager:
    """Manages intermediate artifacts with consistent naming."""
    
    def __init__(self, intermediates_dir: str, output_dir: str):
        self.intermediates_dir = intermediates_dir
        self.output_dir = output_dir
        os.makedirs(intermediates_dir, exist_ok=True)
    
    def save(self, filename: str, data: Any) -> str:
        """Saves data to intermediates directory."""
        path = os.path.join(self.intermediates_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                f.write(data)
            elif isinstance(data, (dict, list)):
                json.dump(data, f, indent=2, default=self._serialize)
            elif hasattr(data, '__dict__'):
                json.dump(data.__dict__, f, indent=2, default=self._serialize)
            else:
                f.write(str(data))
        return path
    
    def load(self, filename: str) -> Optional[Any]:
        """Loads data from intermediates directory."""
        path = os.path.join(self.intermediates_dir, filename)
        if not os.path.exists(path):
            return None
        
        with open(path, "r", encoding="utf-8") as f:
            if filename.endswith('.json'):
                return json.load(f)
            return f.read()
    
    def exists(self, filename: str) -> bool:
        """Checks if intermediate file exists."""
        return os.path.exists(os.path.join(self.intermediates_dir, filename))
    
    def list_saved(self) -> List[str]:
        """Lists all saved intermediate files."""
        if not os.path.exists(self.intermediates_dir):
            return []
        return sorted(os.listdir(self.intermediates_dir))
    
    def _serialize(self, obj: Any) -> Any:
        """Custom serializer for complex objects."""
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        return str(obj)
    
    # Convenience methods for standard intermediates
    def save_tasks(self, tasks: List) -> str:
        return self.save(IntermediateFiles.TASKS, [t.__dict__ for t in tasks])
    
    def save_interfaces(self, interfaces: List) -> str:
        return self.save(IntermediateFiles.INTERFACES, interfaces)
    
    def save_architecture(self, arch: Any, is_initial: bool = False) -> str:
        filename = IntermediateFiles.INITIAL_ARCH if is_initial else IntermediateFiles.FINAL_ARCH
        return self.save(filename, arch)
    
    def save_design_analysis(self, analysis: Any) -> str:
        return self.save(IntermediateFiles.DESIGN_ANALYSIS, analysis)
    
    def save_data(self, data: Any) -> str:
        return self.save(IntermediateFiles.GENERATED_DATA, data)
    
    def save_instrumentation(self, specs: Any) -> str:
        return self.save(IntermediateFiles.INSTRUMENTATION, specs)
