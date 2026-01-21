"""
TDD Tests for Instrumentation & Evaluator Generators (Phase 5)

Tests IInstrumentationGenerator and IEvaluatorGenerator.
Following PROMPT_INSTRUMENTATION_ANALYSIS, PROMPT_INSTRUMENTATION_CODE, PROMPT_INSTRUMENTATION_EVALUATOR.
"""
import unittest
from unittest.mock import MagicMock
import json

import sys
sys.path.insert(0, '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro')

from src.interfaces import ILLMProvider


class TestInstrumentationGeneratorInterface(unittest.TestCase):
    """Tests for IInstrumentationGenerator interface."""
    
    def test_interface_exists(self):
        """IInstrumentationGenerator interface should be importable."""
        from src.interfaces import IInstrumentationGenerator
        self.assertTrue(hasattr(IInstrumentationGenerator, 'analyze'))
        self.assertTrue(hasattr(IInstrumentationGenerator, 'inject'))


class TestEvaluatorGeneratorInterface(unittest.TestCase):
    """Tests for IEvaluatorGenerator interface."""
    
    def test_interface_exists(self):
        """IEvaluatorGenerator interface should be importable."""
        from src.interfaces import IEvaluatorGenerator
        self.assertTrue(hasattr(IEvaluatorGenerator, 'generate'))


class TestLLMInstrumentationGenerator(unittest.TestCase):
    """Tests for LLMInstrumentationGenerator."""
    
    def setUp(self):
        self.mock_llm = MagicMock(spec=ILLMProvider)
        
    def _create_analysis_response(self, specs):
        return json.dumps({
            "requirements": specs
        })
        
    def test_analyzes_logic_for_instrumentation(self):
        """Should analyze if tasks need instrumentation."""
        from src.generators.instrumentation_generator import LLMInstrumentationGenerator
        from types import SimpleNamespace
        
        mock_specs = [{
            "task_id": "task_1",
            "needs_instrumentation": True,
            "required_variables": [{"variable_name": "task1_done", "set_in_function": "finish", "set_condition": "always"}]
        }]
        self.mock_llm.prompt.return_value = self._create_analysis_response(mock_specs)
        
        generator = LLMInstrumentationGenerator(self.mock_llm)
        
        spec = SimpleNamespace(tasks=[SimpleNamespace(id="task_1", description="Do something")])
        logic_code = "function finish() {}"
        
        result = generator.analyze(spec, logic_code)
        
        self.assertGreater(len(result.requirements), 0)
        self.assertTrue(result.requirements[0]['needs_instrumentation'])
        
    def test_injects_instrumentation_code(self):
        """Should inject code into logic."""
        from src.generators.instrumentation_generator import LLMInstrumentationGenerator
        from types import SimpleNamespace
        
        # Mocking the code return directly as prompt returns the code string
        self.mock_llm.prompt.return_value = "function finish() { localStorage.setItem('v', '1'); }"
        
        generator = LLMInstrumentationGenerator(self.mock_llm)
        
        instr_spec = SimpleNamespace(requirements=[{"id": "req1"}])
        logic_code = "function finish() {}"
        
        result = generator.inject(logic_code, instr_spec)
        
        self.assertIn("localStorage", result)
        
    def test_uses_correct_prompt_for_analysis(self):
        """Should use PROMPT_INSTRUMENTATION_ANALYSIS."""
        from src.generators.instrumentation_generator import LLMInstrumentationGenerator
        from types import SimpleNamespace
        
        self.mock_llm.prompt.return_value = self._create_analysis_response([])
        
        generator = LLMInstrumentationGenerator(self.mock_llm)
        spec = SimpleNamespace(tasks=[])
        
        generator.analyze(spec, "")
        
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("analyzing javascript business logic", call_args.lower())


class TestLLMEvaluatorGenerator(unittest.TestCase):
    """Tests for LLMEvaluatorGenerator."""
    
    def setUp(self):
        self.mock_llm = MagicMock(spec=ILLMProvider)
        
    def _create_evaluator_response(self, evaluators):
        return json.dumps({
            "evaluators": evaluators
        })
        
    def test_generates_evaluators(self):
        """Should generate evaluator logic for tasks."""
        from src.generators.evaluator_generator import LLMEvaluatorGenerator
        from types import SimpleNamespace
        
        mock_evals = [{
            "task_id": "task_1",
            "evaluation_logic": "return true;"
        }]
        self.mock_llm.prompt.return_value = self._create_evaluator_response(mock_evals)
        
        generator = LLMEvaluatorGenerator(self.mock_llm)
        
        spec = SimpleNamespace(tasks=[SimpleNamespace(id="task_1")])
        instr_spec = SimpleNamespace(requirements=[]) # Can be None/Empty
        logic_code = ""
        
        result = generator.generate(spec, instr_spec, logic_code)
        
        self.assertIn("task_1", result)
        self.assertIn("return true", result)

    def test_uses_correct_prompt(self):
        """Should use PROMPT_INSTRUMENTATION_EVALUATOR."""
        from src.generators.evaluator_generator import LLMEvaluatorGenerator
        from types import SimpleNamespace
        
        self.mock_llm.prompt.return_value = self._create_evaluator_response([])
        
        generator = LLMEvaluatorGenerator(self.mock_llm)
        spec = SimpleNamespace(tasks=[])
        instr_spec = SimpleNamespace(requirements=[])
        
        generator.generate(spec, instr_spec, "")
        
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("generating evaluators", call_args.lower())


if __name__ == '__main__':
    unittest.main()
