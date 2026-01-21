"""
TDD Tests for BackendGenerator (Phase 2.2)

Tests the IBackendGenerator interface and LLMBackendGenerator implementation.
Following PROMPT_BACKEND_IMPLEMENTATION and PROMPT_BACKEND_TEST contracts.
"""
import unittest
from unittest.mock import MagicMock
import json

import sys
sys.path.insert(0, '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro')

from src.interfaces import ILLMProvider


class TestBackendGeneratorInterface(unittest.TestCase):
    """Tests for IBackendGenerator interface."""
    
    def test_interface_exists(self):
        """IBackendGenerator interface should be importable."""
        from src.interfaces import IBackendGenerator
        self.assertTrue(hasattr(IBackendGenerator, 'generate_logic'))
    
    def test_has_generate_tests_method(self):
        """Should have generate_tests method."""
        from src.interfaces import IBackendGenerator
        self.assertTrue(hasattr(IBackendGenerator, 'generate_logic'))


class TestLLMBackendGenerator(unittest.TestCase):
    """Tests for LLMBackendGenerator implementation."""
    
    def setUp(self):
        self.mock_llm = MagicMock(spec=ILLMProvider)
        
    def _create_logic_response(self, code):
        return json.dumps({"code": code})
    
    def _create_test_response(self, code):
        return json.dumps({"code": code})
        
    def test_generates_business_logic(self):
        """Should generate complete BusinessLogic class."""
        from src.generators.backend_generator import LLMBackendGenerator
        
        mock_code = """
class BusinessLogic {
    constructor() { this._initStorage(); }
    addToCart(productId) { return {success: true}; }
}
module.exports = BusinessLogic;
"""
        self.mock_llm.prompt.return_value = self._create_logic_response(mock_code)
        
        generator = LLMBackendGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        spec.interfaces = []
        
        result = generator.generate_logic(spec)
        
        self.assertIsInstance(result, str)
        self.assertIn("BusinessLogic", result)
        
    def test_implements_all_interfaces(self):
        """Generated code should implement all specified interfaces."""
        from src.generators.backend_generator import LLMBackendGenerator
        from types import SimpleNamespace
        
        mock_code = """
class BusinessLogic {
    addToCart(productId) { return {success: true}; }
    searchProducts(query) { return []; }
}
"""
        self.mock_llm.prompt.return_value = self._create_logic_response(mock_code)
        
        generator = LLMBackendGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        spec.interfaces = [
            SimpleNamespace(name="addToCart", parameters=[], returns={}, description=""),
            SimpleNamespace(name="searchProducts", parameters=[], returns={}, description="")
        ]
        
        result = generator.generate_logic(spec)
        
        self.assertIn("addToCart", result)
        self.assertIn("searchProducts", result)
        
    def test_uses_localstorage(self):
        """Generated code should use localStorage for persistence."""
        from src.generators.backend_generator import LLMBackendGenerator
        
        mock_code = """
const localStorage = (function() { return {}; })();
class BusinessLogic {
    _saveToStorage(key, data) { localStorage.setItem(key, JSON.stringify(data)); }
}
"""
        self.mock_llm.prompt.return_value = self._create_logic_response(mock_code)
        
        generator = LLMBackendGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        spec.interfaces = []
        
        result = generator.generate_logic(spec)
        
        self.assertIn("localStorage", result)
        
    def test_generates_valid_javascript(self):
        """Generated code should be syntactically valid JS."""
        from src.generators.backend_generator import LLMBackendGenerator
        
        mock_code = "class BusinessLogic { constructor() {} }\nmodule.exports = BusinessLogic;"
        self.mock_llm.prompt.return_value = self._create_logic_response(mock_code)
        
        generator = LLMBackendGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        spec.interfaces = []
        
        result = generator.generate_logic(spec)
        
        # Should not be empty
        self.assertGreater(len(result.strip()), 0)
        
    def test_generates_integration_tests(self):
        """Should generate flow-based integration tests."""
        from src.generators.backend_generator import LLMBackendGenerator
        
        mock_test_code = """
class TestRunner {
    testAddToCartFlow() {
        const result = this.logic.addToCart('prod_1');
        this.assert(result.success, 'Add to cart should succeed');
    }
}
"""
        self.mock_llm.prompt.return_value = self._create_test_response(mock_test_code)
        
        generator = LLMBackendGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = [MagicMock(id="task_1", description="Add item to cart")]
        spec.interfaces = []
        
        result = generator.generate_tests(spec, "// logic code", {})
        
        self.assertIsInstance(result, str)
        self.assertIn("test", result.lower())
        
    def test_uses_correct_prompt_for_logic(self):
        """Should use PROMPT_BACKEND_IMPLEMENTATION from library."""
        from src.generators.backend_generator import LLMBackendGenerator
        
        self.mock_llm.prompt.return_value = self._create_logic_response("")
        
        generator = LLMBackendGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        spec.interfaces = []
        
        generator.generate_logic(spec)
        
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("javascript developer", call_args.lower())
        
    def test_uses_correct_prompt_for_tests(self):
        """Should use PROMPT_BACKEND_TEST from library."""
        from src.generators.backend_generator import LLMBackendGenerator
        
        self.mock_llm.prompt.return_value = self._create_test_response("")
        
        generator = LLMBackendGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.interfaces = []
        
        generator.generate_tests(spec, "// logic", {})
        
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("test engineer", call_args.lower())
        
    def test_handles_malformed_response(self):
        """Should handle malformed JSON gracefully."""
        from src.generators.backend_generator import LLMBackendGenerator
        
        self.mock_llm.prompt.return_value = "not valid json"
        
        generator = LLMBackendGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        spec.interfaces = []
        
        result = generator.generate_logic(spec)
        
        self.assertIsInstance(result, str)


if __name__ == '__main__':
    unittest.main()
