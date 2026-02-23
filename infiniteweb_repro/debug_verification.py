import asyncio
import os
import sys
import json

# Add current directory to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.generators.verification_generator import VerificationGenerator
from src.domain import Task
from src.llm import CustomLLMProvider

# Setup paths
OUTPUT_DIR = "output/glm4_full_run_unbuffered_fixed_8"
INTERMEDIATES_DIR = os.path.join(OUTPUT_DIR, "intermediates")

async def main():
    print("🚀 Starting Debug Verification...")
    
    # Initialize LLM
    base_url = "https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47-tool-fork/v1"
    model_name = "glm-4"
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_API_KEY"] = "EMPTY"  
    
    llm = CustomLLMProvider(base_url=base_url, model=model_name)
    
    # Load Artifacts
    print("📂 Loading artifacts...")
    
    # Load Task
    # We use the tasks.json from the output root which we verified contains the steps
    with open(os.path.join(OUTPUT_DIR, "tasks.json")) as f:
        tasks_data = json.load(f)
        task_data = tasks_data[0] # task_1
        task = Task.from_dict(task_data)
        print(f"✅ Loaded Task: {task.id}")
        
    # Load Architecture
    # Try loading from intermediates
    arch_path = os.path.join(INTERMEDIATES_DIR, "4_final_architecture.json")
    if not os.path.exists(arch_path):
        # Fallback to initial if final not present (though it should be)
         arch_path = os.path.join(INTERMEDIATES_DIR, "2_initial_architecture.json")
         
    with open(arch_path) as f:
        architecture = json.load(f)
        print(f"✅ Loaded Architecture from {arch_path}")

    # Load HTML
    with open(os.path.join(OUTPUT_DIR, "index.html")) as f:
        html_content = f.read()
        print("✅ Loaded index.html")

    # Load Logic
    with open(os.path.join(OUTPUT_DIR, "logic.js")) as f:
        logic_code = f.read()
        print("✅ Loaded logic.js")
        
    # Initialize Generator
    verifier = VerificationGenerator(llm)
    
    # Run Golden Path Generation
    print("🧪 Generating Golden Path...")
    golden_path = verifier.generate_golden_path(task, architecture, html_content, logic_code)
    
    if golden_path:
        print("\n✨ Generated Golden Path:")
        print(json.dumps(golden_path, indent=2))
        
        # Check for Add to Cart
        steps = golden_path.get("steps", [])
        has_add_to_cart = any("add-to-cart" in s.get("selector", "") or "Add to Cart" in s.get("description", "") for s in steps)
        
        if has_add_to_cart:
             print("\n✅ SUCCESS: 'Add to Cart' step found!")
        else:
             print("\n❌ FAILURE: 'Add to Cart' step MISSING.")
    else:
        print("\n❌ Failed to generate golden path (None returned).")

if __name__ == "__main__":
    asyncio.run(main())
