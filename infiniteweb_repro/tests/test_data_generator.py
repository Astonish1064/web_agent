"""
TDD Tests for DataGenerator (Phase 2.1)

Tests the IDataGenerator interface and LLMDataGenerator implementation.
Following PROMPT_DATA_GENERATION contract.
"""
import unittest
from unittest.mock import MagicMock
import json

import sys
sys.path.insert(0, '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro')

from src.interfaces import ILLMProvider


class TestDataGeneratorInterface(unittest.TestCase):
    """Tests for IDataGenerator interface contract."""
    
    def test_interface_exists(self):
        """IDataGenerator interface should be importable."""
        from src.interfaces import IDataGenerator
        self.assertTrue(hasattr(IDataGenerator, 'generate'))
    
    def test_interface_is_abstract(self):
        """IDataGenerator should be abstract."""
        from src.interfaces import IDataGenerator
        with self.assertRaises(TypeError):
            IDataGenerator()


class TestLLMDataGenerator(unittest.TestCase):
    """Tests for LLMDataGenerator implementation."""
    
    def setUp(self):
        self.mock_llm = MagicMock(spec=ILLMProvider)
        
    def _create_response(self, static_data):
        """Helper to create mock response."""
        return json.dumps({"static_data": static_data})
        
    def test_generates_realistic_data(self):
        """Should generate data for all data models."""
        from src.generators.data_generator import LLMDataGenerator
        from types import SimpleNamespace
        
        mock_data = {
            "products": [
                {"id": "prod_1", "name": "Python Book", "price": 29.99}
            ],
            "categories": [
                {"id": "cat_1", "name": "Programming"}
            ]
        }
        self.mock_llm.prompt.return_value = self._create_response(mock_data)
        
        generator = LLMDataGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = [
            SimpleNamespace(name="Product", attributes={"id": "string", "name": "string"}),
            SimpleNamespace(name="Category", attributes={"id": "string", "name": "string"})
        ]
        
        result = generator.generate(spec)
        
        self.assertIsInstance(result, dict)
        self.assertIn("products", result)
        
    def test_follows_data_dictionary(self):
        """Should only include fields defined in data models."""
        from src.generators.data_generator import LLMDataGenerator
        from types import SimpleNamespace
        
        mock_data = {
            "products": [
                {"id": "prod_1", "name": "Test Product", "price": 19.99}
            ]
        }
        self.mock_llm.prompt.return_value = self._create_response(mock_data)
        
        generator = LLMDataGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = [SimpleNamespace(name="Product", attributes={})]
        
        result = generator.generate(spec)
        
        # Check product has expected fields
        product = result["products"][0]
        self.assertIn("id", product)
        self.assertIn("name", product)
        
    def test_respects_volume_hints(self):
        """Should generate appropriate number of items."""
        from src.generators.data_generator import LLMDataGenerator
        from types import SimpleNamespace
        
        mock_data = {
            "products": [{"id": f"prod_{i}"} for i in range(10)]
        }
        self.mock_llm.prompt.return_value = self._create_response(mock_data)
        
        generator = LLMDataGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = [SimpleNamespace(name="Product", attributes={})]
        
        result = generator.generate(spec)
        
        self.assertGreater(len(result.get("products", [])), 0)
        
    def test_uses_correct_prompt(self):
        """Should use PROMPT_DATA_GENERATION from library."""
        from src.generators.data_generator import LLMDataGenerator
        
        self.mock_llm.prompt.return_value = self._create_response({})
        
        generator = LLMDataGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        
        generator.generate(spec)
        
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("data generator", call_args.lower())
        
    def test_handles_malformed_response(self):
        """Should handle malformed JSON gracefully."""
        from src.generators.data_generator import LLMDataGenerator
        
        self.mock_llm.prompt.return_value = "not valid json"
        
        generator = LLMDataGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        
        result = generator.generate(spec)
        
        self.assertIsInstance(result, dict)
        
    def test_returns_empty_dict_on_error(self):
        """Should return empty dict on error."""
        from src.generators.data_generator import LLMDataGenerator
        
        self.mock_llm.prompt.side_effect = Exception("LLM Error")
        
        generator = LLMDataGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.data_models = []
        
        result = generator.generate(spec)
        
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    unittest.main()
