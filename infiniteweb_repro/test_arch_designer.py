
import asyncio
import os
import sys

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import CustomLLMProvider
from src.generators.architecture_designer import LLMArchitectDesigner, Architecture
from src.domain import Task, WebsiteSpec

def test_arch_design():
    print("🧪 Testing LLMArchitectDesigner...")
    
    # Setup LLM
    base_url = "https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47-tool-fork/v1"
    model_name = "glm-4"
    
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_MODEL"] = f"openai/{model_name}"
    os.environ["LLM_API_KEY"] = "EMPTY"
    
    llm = CustomLLMProvider(base_url=base_url, model=model_name)
    designer = LLMArchitectDesigner(llm)
    
    # Mock Spec
    spec = WebsiteSpec(
        seed="simple_todo_app",
        tasks=[
            Task(id="t1", name="Add Task", description="Add a new task", steps=[]),
            Task(id="t2", name="Delete Task", description="Remove a task", steps=[])
        ]
    )
    
    print("Invoking design()...")
    arch = designer.design(spec)
    print("✅ Design complete!")
    print(arch)

if __name__ == "__main__":
    test_arch_design() # It's synchronous actually according to code, but let's check
