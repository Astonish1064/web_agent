
import pytest
import json
from unittest.mock import MagicMock
from src.generators.evaluator_generator import LLMEvaluatorGenerator
from src.interfaces import ILLMProvider
from src.domain import Task

class MockLLM(ILLMProvider):
    def prompt(self, prompt: str, **kwargs) -> str:
        # Match PROMPT_INSTRUMENTATION_EVALUATOR
        if "generating evaluators" in prompt or "INSTRUMENTATION VARIABLES AVAILABLE" in prompt:
            return json.dumps({
                "evaluators": [
                    {
                        "task_id": "task_1",
                        "name": "Task 1 Evaluator",
                        "evaluation_logic": "return localStorage.getItem('task1_step1') === 'true';"
                    }
                ]
            })
        return ""
    
    def prompt_json(self, prompt: str, **kwargs):
        pass

def test_generate():
    llm = MockLLM()
    gen = LLMEvaluatorGenerator(llm)
    
    spec = MagicMock()
    spec.tasks = [Task(id="task_1", name="Test Task", description="Test Task", steps=["step1"])]
    spec.data_models = []
    
    instr_spec = MagicMock()
    instr_spec.requirements = [
        {"task_id": "task_1", "needs_instrumentation": True, "required_variables": [{"variable_name": "task1_step1"}]}
    ]
    
    logic_code = "class BusinessLogic {}"
    
    eval_js = gen.generate(spec, instr_spec, logic_code)
    
    assert "class Evaluator" in eval_js
    assert "task1_step1" in eval_js
    assert "localStorage.getItem" in eval_js

if __name__ == "__main__":
    test_generate()
    print("All tests passed!")
