
import pytest
import json
from unittest.mock import MagicMock
from src.generators.instrumentation_generator import LLMInstrumentationGenerator, InstrumentationRequirements
from src.interfaces import ILLMProvider
from src.domain import Task

class MockLLM(ILLMProvider):
    def prompt(self, prompt: str, **kwargs) -> str:
        # Match PROMPT_INSTRUMENTATION_ANALYSIS
        if "analyzing JavaScript business logic" in prompt or "INSTRUMENTATION GUIDELINES" in prompt:
            return json.dumps({
                "requirements": [
                    {
                        "task_id": "task_1",
                        "needs_instrumentation": True,
                        "required_variables": [
                            {
                                "variable_name": "task1_step1",
                                "set_in_function": "doSomething",
                                "set_condition": "always"
                            }
                        ]
                    }
                ]
            })
        # Match PROMPT_INSTRUMENTATION_CODE
        if "adding instrumentation variables" in prompt or "ORIGINAL CODE" in prompt:
            return """
class BusinessLogic {
    doSomething() {
        try {
            localStorage.setItem('task1_step1', 'true');
            window.__instrumentation = window.__instrumentation || {};
            window.__instrumentation['task1_step1'] = 'true';
        } catch(e) {}
        console.log("Did something");
    }
}
"""
        return ""
    
    def prompt_json(self, prompt: str, **kwargs):
        pass

def test_analyze():
    llm = MockLLM()
    gen = LLMInstrumentationGenerator(llm)
    
    spec = MagicMock()
    spec.tasks = [Task(id="task_1", name="Test Task", description="Test Task", steps=["step1"])]
    
    logic_code = "class BusinessLogic { doSomething() {} }"
    
    reqs = gen.analyze(spec, logic_code)
    assert len(reqs.requirements) == 1
    assert reqs.requirements[0]["task_id"] == "task_1"

def test_inject():
    llm = MockLLM()
    gen = LLMInstrumentationGenerator(llm)
    
    logic_code = "class BusinessLogic { doSomething() {} }"
    reqs = InstrumentationRequirements(requirements=[{"task_id": "task_1"}])
    
    new_code = gen.inject(logic_code, reqs)
    assert "window.__instrumentation" in new_code
    assert "task1_step1" in new_code

if __name__ == "__main__":
    # Manually run if pytest not available or for quick check
    test_analyze()
    test_inject()
    print("All tests passed!")
