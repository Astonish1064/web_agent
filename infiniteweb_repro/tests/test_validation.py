import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
# will fail here because SchemaValidator is not implemented yet
try:
    from src.validation import SchemaValidator
except ImportError:
    SchemaValidator = None


class TestSchemaValidator(unittest.TestCase):
    
    def test_validate_task_structure_valid(self):
        """Should return True for valid task structure."""
        valid_tasks = [
            {"id": "t1", "name": "Task 1", "description": "Desc", "steps": ["s1", "s2"]}
        ]
        self.assertTrue(SchemaValidator.validate_tasks(valid_tasks))

    def test_validate_task_structure_invalid_missing_field(self):
        """Should return False if required fields are missing."""
        invalid_tasks = [
            {"id": "t1", "description": "Missing name"} 
        ]
        self.assertFalse(SchemaValidator.validate_tasks(invalid_tasks))

    def test_validate_task_structure_invalid_type(self):
        """Should return False if field types are wrong."""
        invalid_tasks = [
            {"id": "t1", "name": "Task 1", "description": "Desc", "steps": "Not a list"}
        ]
        self.assertFalse(SchemaValidator.validate_tasks(invalid_tasks))
        
    def test_validate_interface_structure_valid(self):
        """Should return True for valid interface structure."""
        valid_interfaces = [
            {"name": "I1", "parameters": [{"name": "p1", "type": "string"}], "description": "Desc"}
        ]
        self.assertTrue(SchemaValidator.validate_interfaces(valid_interfaces))
