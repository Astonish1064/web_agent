
import unittest
from unittest.mock import MagicMock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.generators.interface_designer import LLMInterfaceDesigner
from src.interfaces import ILLMProvider
import json

class TestInterfaceDesignerRobustness(unittest.TestCase):
    
    def setUp(self):
        self.mock_llm = MagicMock(spec=ILLMProvider)
    
    def _create_design_response(self, interfaces, helpers=None):
        return json.dumps({
            "interfaces": interfaces,
            "helperFunctions": helpers or []
        })

    def test_rejects_invalid_interfaces(self):
        """Should reject interfaces missing required fields."""
        # Missing 'parameters'
        mock_interfaces = [{
            "name": "badInterface",
            "description": "Missing params",
            "returns": {"type": "void"}
        }]
        self.mock_llm.prompt.return_value = self._create_design_response(mock_interfaces)
        
        designer = LLMInterfaceDesigner(self.mock_llm)
        spec = MagicMock()
        # Mocking spec attributes to avoid errors during prompt generation
        spec.tasks = []
        spec.data_models = []
        spec.pages = []
        spec.seed = "test"
        
        result = designer.design(spec)
        
        # design() catches the retry failure (None) and returns []
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
