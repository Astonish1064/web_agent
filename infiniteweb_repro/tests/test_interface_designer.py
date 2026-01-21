"""
TDD Tests for InterfaceDesigner (Phase 1.2)

Tests the IInterfaceDesigner interface and LLMInterfaceDesigner implementation.
Following PROMPT_INTERFACE_DESIGN and PROMPT_INTERFACE_WRAPPING contracts.
"""
import unittest
from unittest.mock import MagicMock
from dataclasses import dataclass
from typing import List, Dict
import json

import sys
sys.path.insert(0, '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro')

from src.interfaces import ILLMProvider


@dataclass
class InterfaceDef:
    """An interface definition."""
    name: str
    description: str
    parameters: List[Dict]
    returns: Dict
    related_tasks: List[str]


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


class TestInterfaceDesignerInterface(unittest.TestCase):
    """Tests for IInterfaceDesigner interface contract."""
    
    def test_interface_exists(self):
        """IInterfaceDesigner interface should be importable."""
        from src.interfaces import IInterfaceDesigner
        self.assertTrue(hasattr(IInterfaceDesigner, 'design'))
        self.assertTrue(hasattr(IInterfaceDesigner, 'wrap'))
    
    def test_interface_is_abstract(self):
        """IInterfaceDesigner should be abstract."""
        from src.interfaces import IInterfaceDesigner
        with self.assertRaises(TypeError):
            IInterfaceDesigner()


class TestLLMInterfaceDesigner(unittest.TestCase):
    """Tests for LLMInterfaceDesigner implementation."""
    
    def setUp(self):
        self.mock_llm = MagicMock(spec=ILLMProvider)
        
    def _create_design_response(self, interfaces, helpers=None):
        """Helper to create mock design response."""
        return json.dumps({
            "interfaces": interfaces,
            "helperFunctions": helpers or []
        })
    
    def _create_wrap_response(self, wrapped, state_models, mapping):
        """Helper to create mock wrap response."""
        return json.dumps({
            "wrapped_interfaces": wrapped,
            "state_data_models": state_models,
            "implementation_mapping": mapping
        })
        
    def test_designs_interfaces_from_tasks(self):
        """Should generate interfaces based on tasks and pages."""
        from src.generators.interface_designer import LLMInterfaceDesigner
        
        mock_interfaces = [{
            "name": "addToCart",
            "description": "Add a product to cart",
            "parameters": [{"name": "productId", "type": "string"}],
            "returns": {"type": "boolean"},
            "relatedTasks": ["task_1"]
        }]
        self.mock_llm.prompt.return_value = self._create_design_response(mock_interfaces)
        
        designer = LLMInterfaceDesigner(self.mock_llm)
        
        # Minimal spec for testing
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = [MagicMock(id="task_1", description="Buy a book")]
        spec.data_models = []
        spec.pages = []
        
        result = designer.design(spec)
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
    def test_interface_has_required_fields(self):
        """Each interface should have name, description, parameters, returns."""
        from src.generators.interface_designer import LLMInterfaceDesigner
        
        mock_interfaces = [{
            "name": "searchProducts",
            "description": "Search for products",
            "parameters": [{"name": "query", "type": "string"}],
            "returns": {"type": "array"},
            "relatedTasks": ["task_1"]
        }]
        self.mock_llm.prompt.return_value = self._create_design_response(mock_interfaces)
        
        designer = LLMInterfaceDesigner(self.mock_llm)
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        spec.pages = []
        
        result = designer.design(spec)
        
        iface = result[0]
        self.assertTrue(hasattr(iface, 'name'))
        self.assertTrue(hasattr(iface, 'description'))
        self.assertTrue(hasattr(iface, 'parameters'))
        self.assertTrue(hasattr(iface, 'returns'))
        
    def test_creates_helper_functions(self):
        """Should return helper functions from LLM response."""
        from src.generators.interface_designer import LLMInterfaceDesigner
        
        mock_interfaces = [{"name": "addToCart", "description": "Add to cart",
                           "parameters": [], "returns": {}, "relatedTasks": []}]
        mock_helpers = [{"name": "_getOrCreateCart", "description": "Internal helper",
                        "visibility": "private"}]
        self.mock_llm.prompt.return_value = self._create_design_response(mock_interfaces, mock_helpers)
        
        designer = LLMInterfaceDesigner(self.mock_llm)
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        spec.pages = []
        
        interfaces, helpers = designer.design_with_helpers(spec)
        
        self.assertGreater(len(helpers), 0)
        self.assertEqual(helpers[0].name, "_getOrCreateCart")
        
    def test_wraps_system_parameters(self):
        """Should wrap interfaces to hide system-managed parameters."""
        from src.generators.interface_designer import LLMInterfaceDesigner, InterfaceDef
        
        wrapped_response = self._create_wrap_response(
            wrapped=[{"name": "addToCart", "parameters": [{"name": "productId", "type": "string"}]}],
            state_models=[{"name": "UserSession", "fields": [{"name": "currentUserId", "type": "string"}]}],
            mapping=[{"wrapped_function": "addToCart", "parameter_mapping": {"userId": "_getSession().currentUserId"}}]
        )
        self.mock_llm.prompt.return_value = wrapped_response
        
        designer = LLMInterfaceDesigner(self.mock_llm)
        
        # Original interfaces with userId - use dataclass instead of MagicMock
        from src.generators.interface_designer import InterfaceDef
        original = [InterfaceDef(
            name="addToCart",
            description="Add to cart",
            parameters=[
                {"name": "userId", "type": "string"},
                {"name": "productId", "type": "string"}
            ],
            returns={},
            related_tasks=[]
        )]
        
        result = designer.wrap(original, [])

        from src.generators.interface_designer import WrappedInterfaces as ActualWrappedInterfaces
        self.assertIsInstance(result, ActualWrappedInterfaces)
        self.assertGreater(len(result.wrapped_interfaces), 0)
        
    def test_uses_correct_prompt(self):
        """Should use PROMPT_INTERFACE_DESIGN from library."""
        from src.generators.interface_designer import LLMInterfaceDesigner
        from src.prompts.library import PROMPT_INTERFACE_DESIGN
        
        self.mock_llm.prompt.return_value = self._create_design_response([])
        
        designer = LLMInterfaceDesigner(self.mock_llm)
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        spec.pages = []
        
        designer.design(spec)
        
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("software architect", call_args.lower())
        
    def test_handles_malformed_response(self):
        """Should handle malformed JSON gracefully."""
        from src.generators.interface_designer import LLMInterfaceDesigner
        
        self.mock_llm.prompt.return_value = "not valid json"
        
        designer = LLMInterfaceDesigner(self.mock_llm)
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        spec.pages = []
        
        result = designer.design(spec)
        
        self.assertIsInstance(result, list)


if __name__ == '__main__':
    unittest.main()
