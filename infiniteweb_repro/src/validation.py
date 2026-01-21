
from typing import List, Dict, Any

class SchemaValidator:
    """Validates generated data structures against expected schema."""
    
    @staticmethod
    def _normalize_keys(d: Dict) -> Dict:
        """Normalize all keys in a dict to lowercase."""
        if not isinstance(d, dict):
            return d
        return {k.lower(): v for k, v in d.items()}
    
    @staticmethod
    def _has_field(d: Dict, field: str) -> bool:
        """Check if field exists (case-insensitive)."""
        return field.lower() in [k.lower() for k in d.keys()]
    
    @staticmethod
    def _get_field(d: Dict, field: str, default=None):
        """Get field value (case-insensitive)."""
        for k, v in d.items():
            if k.lower() == field.lower():
                return v
        return default
    
    @staticmethod
    def validate_tasks(tasks: List[Dict[str, Any]]) -> bool:
        """
        Validates a list of tasks.
        Required fields: id OR name (at minimum)
        Optional: description, steps/required_steps
        """
        if not isinstance(tasks, list):
            return False
        
        if len(tasks) == 0:
            return False  # At least one task required
            
        for task in tasks:
            if not isinstance(task, dict):
                return False
            
            # Must have at least id or name
            has_id = SchemaValidator._has_field(task, "id")
            has_name = SchemaValidator._has_field(task, "name")
            
            if not has_id and not has_name:
                print(f"[Validation] Task missing both id and name")
                return False
            
            # Accept steps OR required_steps
            has_steps = SchemaValidator._has_field(task, "steps") or SchemaValidator._has_field(task, "required_steps")
            # Steps not strictly required - just log warning
            if not has_steps:
                print(f"[Validation] Task missing steps field (non-fatal)")
                
        return True

    @staticmethod
    def validate_interfaces(interfaces: List[Dict[str, Any]]) -> bool:
        """
        Validates a list of interfaces.
        Required fields: name, description, parameters (list)
        """
        if not isinstance(interfaces, list):
            return False
            
        for interface in interfaces:
            if not isinstance(interface, dict):
                return False
                
            required_fields = ["name", "description", "parameters"]
            for field in required_fields:
                if not SchemaValidator._has_field(interface, field):
                    print(f"[Validation] Interface missing field: {field} in {interface.get('name', 'unknown')}")
                    return False
            
            # Check types (case-insensitive get)
            params = SchemaValidator._get_field(interface, "parameters", [])
            if not isinstance(params, list):
                return False
                
        return True

