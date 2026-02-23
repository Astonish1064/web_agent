
import asyncio
import os
import sys
import json
import logging

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import CustomLLMProvider
from src.domain import Task
from src.agent.environments.playwright_env import PlaywrightEnvironment
from src.agent.agents.llm_agent import LLMWebAgent
from src.agent.runner import AgentRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Setup Paths
OUTPUT_DIR = "output/pipeline_v2_test"
TASKS_FILE = os.path.join(OUTPUT_DIR, "intermediates/01_tasks.json")

async def main():
    print(f"🔍 Loading tasks from {TASKS_FILE}...")
    if not os.path.exists(TASKS_FILE):
        print(f"❌ Tasks file not found: {TASKS_FILE}")
        return

    # 1. Load Tasks
    with open(TASKS_FILE, "r") as f:
        tasks_data = json.load(f)
    
    # Handle list or dict wrapper
    if isinstance(tasks_data, dict) and "tasks" in tasks_data:
         tasks_data = tasks_data["tasks"]
    
    tasks = [Task.from_dict(t) for t in tasks_data]
    
    # Filter for Task 1 and Task 2
    target_tasks = [t for t in tasks if t.id in ["task_1", "task_2"]]
    print(f"📋 Loaded {len(target_tasks)} tasks to verify: {[t.id for t in target_tasks]}")

    # 2. Setup LLM
    # Using environment variables or hardcoded fallback (matching test_pipeline_v2.py)
    base_url = os.environ.get("LLM_BASE_URL", "https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47-tool-fork/v1")
    model_name = os.environ.get("LLM_MODEL", "glm-4").replace("openai/", "")
    
    # Environment setup
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_MODEL"] = f"openai/{model_name}"
    os.environ["LLM_API_KEY"] = "EMPTY"
    os.environ["SANDBOX_TYPE"] = "local"
    
    print(f"🤖 Initializing LLM ({model_name})...")
    llm = CustomLLMProvider(base_url=base_url, model=model_name)

    # 3. Setup Environment
    print("🌍 Initializing Playwright Environment...")
    env = PlaywrightEnvironment(headless=True)
    
    # 4. Setup Agent
    print("🕵️ Initializing LLM Web Agent...")
    agent = LLMWebAgent(llm=llm)

    # 5. Setup Runner
    runner = AgentRunner(env, agent, OUTPUT_DIR)

    # 6. Run Tasks
    results = {}
    try:
        for task in target_tasks:
            print(f"\n" + "="*60)
            print(f"🚀 Verifying {task.id}: {task.name}")
            print("="*60)
            print(f"Goal: {task.description}")
            
            result = await runner.run_task(OUTPUT_DIR, task, max_steps=10)
            results[task.id] = result
            
            status = "✅ PASSED" if result.success else "❌ FAILED"
            print(f"\nResult for {task.id}: {status}")
            print(f"Steps taken: {result.steps}")
            print(f"Total reward: {result.total_reward}")
            
            if not result.success:
                 print("\nTrajectory Summary:")
                 for step in result.trajectory:
                     print(f"  - {step.action.type}({step.action.target}) -> {step.info}")
    finally:
        # Cleanup
        print("\n🧹 Cleaning up environment...")
        await env.stop()

    # Final Summary
    print("\n" + "="*60)
    print("📊 Verification Summary")
    print("="*60)
    all_passed = True
    for task_id, result in results.items():
        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"{task_id}: {status}")
        if not result.success:
            all_passed = False
            
    if all_passed:
        print("\n✅ All target tasks passed autonomous verification.")
        sys.exit(0)
    else:
        print("\n❌ Some tasks failed verification.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
