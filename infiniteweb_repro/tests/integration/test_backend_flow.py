"""
Integration Tests: Backend Phase Flow

Tests collaboration between:
- DataGenerator → BackendGenerator → InstrumentationGenerator
"""
import unittest
from unittest.mock import MagicMock
import json

import sys
sys.path.insert(0, '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro')

from src.generators.data_generator import LLMDataGenerator
from src.generators.backend_generator import LLMBackendGenerator
from src.generators.instrumentation_generator import LLMInstrumentationGenerator
from src.domain import WebsiteSpec
from types import SimpleNamespace


class TestBackendPhaseIntegration(unittest.TestCase):
    """Integration tests for Backend Phase."""
    
    def setUp(self):
        self.mock_llm = MagicMock()
        self.data_gen = LLMDataGenerator(self.mock_llm)
        self.backend_gen = LLMBackendGenerator(self.mock_llm)
        self.instr_gen = LLMInstrumentationGenerator(self.mock_llm)
    
    def test_data_to_backend_integration(self):
        """Test that generated data flows to backend implementation."""
        # Generate data
        spec = SimpleNamespace(
            seed="store",
            tasks=[],
            data_models=[SimpleNamespace(name="Product", attributes={"id": "string", "name": "string"})]
        )
        
        data_response = json.dumps({
            "static_data": {
                "products": [{"id": "p1", "name": "Item 1"}]
            }
        })
        self.mock_llm.prompt.return_value = data_response
        generated_data = self.data_gen.generate(spec)
        
        # Verify data was generated
        self.assertIn("products", generated_data)
        
        # Generate backend using spec with data_models
        backend_response = json.dumps({
            "code": "class BusinessLogic { getProducts() { return JSON.parse(localStorage.getItem('products')); } }"
        })
        self.mock_llm.prompt.return_value = backend_response
        
        spec.interfaces = []
        backend_code = self.backend_gen.generate_logic(spec)
        
        # Verify backend references data model
        self.assertIn("products", backend_code.lower())
        
        # Verify backend_gen received data_models in prompt
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("Product", call_args)
    
    def test_backend_instrumentation_flow(self):
        """Test Backend → Instrumentation analysis → Injection flow."""
        # Step 1: Generate backend logic
        spec = SimpleNamespace(
            seed="store",
            tasks=[SimpleNamespace(id="t1", description="Add to cart")],
            data_models=[],
            interfaces=[]
        )
        
        backend_code = "class BusinessLogic { addToCart(id) { return {success: true}; } }"
        self.mock_llm.prompt.return_value = json.dumps({"code": backend_code})
        logic = self.backend_gen.generate_logic(spec)
        
        # Step 2: Analyze for instrumentation
        analysis_response = json.dumps({
            "requirements": [{
                "task_id": "t1",
                "needs_instrumentation": True,
                "required_variables": [{
                    "variable_name": "t1_cartUpdated",
                    "set_in_function": "addToCart",
                    "set_condition": "after success"
                }]
            }]
        })
        self.mock_llm.prompt.return_value = analysis_response
        instr_reqs = self.instr_gen.analyze(spec, logic)
        
        # Verify analysis found requirements
        self.assertEqual(len(instr_reqs.requirements), 1)
        self.assertTrue(instr_reqs.requirements[0]['needs_instrumentation'])
        
        # Step 3: Inject instrumentation
        injected_code = "class BusinessLogic { addToCart(id) { localStorage.setItem('t1_cartUpdated', 'true'); return {success: true}; } }"
        self.mock_llm.prompt.return_value = injected_code
        
        final_code = self.instr_gen.inject(logic, instr_reqs)
        
        # Verify injection occurred
        self.assertIn("localStorage", final_code)
        self.assertIn("t1_cartUpdated", final_code)


class TestBackendTestGeneration(unittest.TestCase):
    """Test backend test generation integration."""
    
    def setUp(self):
        self.mock_llm = MagicMock()
        self.backend_gen = LLMBackendGenerator(self.mock_llm)
    
    def test_backend_test_generation_flow(self):
        """Test that backend tests are generated from logic + data."""
        spec = SimpleNamespace(
            seed="store",
            tasks=[SimpleNamespace(id="t1", description="Search")],
            interfaces=[SimpleNamespace(name="search")]
        )
        
        logic_code = "class BusinessLogic { search(q) { return []; } }"
        generated_data = {"products": [{"id": "p1"}]}
        
        test_response = json.dumps({
            "code": "class TestRunner { testSearch() { const r = logic.search('test'); assert(Array.isArray(r)); } }"
        })
        self.mock_llm.prompt.return_value = test_response
        
        test_code = self.backend_gen.generate_tests(spec, logic_code, generated_data)
        
        # Verify test code generated
        self.assertIn("test", test_code.lower())
        self.assertIn("search", test_code.lower())


if __name__ == '__main__':
    unittest.main()
