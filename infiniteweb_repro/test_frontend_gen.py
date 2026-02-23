
import os
import sys
import json

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import CustomLLMProvider
from src.generators.frontend_generator import LLMFrontendGenerator
from src.domain import Task, WebsiteSpec, PageSpec, InterfaceDef

def test_frontend_generation():
    print("🧪 Testing LLMFrontendGenerator with Multi-Page support...")
    
    # Setup LLM
    base_url = "https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47-tool-fork/v1"
    model_name = "glm-4"
    
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_MODEL"] = f"openai/{model_name}"
    os.environ["LLM_API_KEY"] = "EMPTY"
    
    llm = CustomLLMProvider(base_url=base_url, model=model_name)
    generator = LLMFrontendGenerator(llm)
    
    # Mock Spec with Architecture
    spec = WebsiteSpec(
        seed="todo_app",
        pages=[
            PageSpec(name="Task List", filename="index.html", description="Lists all tasks"),
            PageSpec(name="Add Task", filename="add.html", description="Form to add a new task")
        ],
        interfaces=[
            InterfaceDef(name="addTask", description="Adds a task", parameters=[], returns={})
        ]
    )
    
    # Mock Task
    task = Task(
        id="t1", 
        name="Add a Task", 
        description="Navigate to the add page and create a new task.",
        steps=[
            "Go to the Add Task page",
            "Fill in the form",
            "Submit"
        ]
    )
    
    logic_code = """
    class BusinessLogic {
        async addTask(title) { return {success: true}; }
    }
    """
    
    print("Invoking implement_task_view()...")
    pages = generator.implement_task_view(task, logic_code, spec)
    
    print(f"✅ Generated {len(pages)} pages:")
    for filename in pages.keys():
        print(f"   - {filename}")
        
    if "add.html" in pages:
        print("🎉 SUCCESS: add.html was generated!")
    else:
        print("❌ FAILURE: add.html was NOT generated.")

if __name__ == "__main__":
    test_frontend_generation()
