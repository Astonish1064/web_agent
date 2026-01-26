import asyncio
import os
import sys
import logging
from src.agent.environments.playwright_env import PlaywrightEnvironment
from src.agent.agents.llm_agent import LLMWebAgent
from src.agent.runner import AgentRunner
from src.llm import CustomLLMProvider
from src.domain import Task

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent.verify")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 verify_agent.py <output_dir> [use_instrumentation=true/false]")
        return

    output_dir = sys.argv[1]
    use_instrumentation = True
    if len(sys.argv) > 2:
        use_instrumentation = sys.argv[2].lower() == "true"
    
    # 1. Setup components
    llm = CustomLLMProvider() # Uses current model in src/llm.py
    env = PlaywrightEnvironment(headless=True)
    agent = LLMWebAgent(llm, use_instrumentation=use_instrumentation)
    runner = AgentRunner(env, agent, output_dir=os.path.join(output_dir, "agent_runs"))

    # 2. Define a mockup task if tasks.json doesn't exist, otherwise load
    tasks_path = os.path.join(output_dir, "tasks.json")
    if os.path.exists(tasks_path):
        import json
        with open(tasks_path, "r") as f:
            tasks_data = json.load(f)
            # Convert to Task objects
            tasks = [Task(id=t.get("id", f"task_{i}"), 
                          description=t.get("description", t.get("name", "")), 
                          complexity=t.get("complexity", 1), 
                          required_steps=t.get("steps", [])) 
                     for i, t in enumerate(tasks_data)]
    else:
        logger.warning("No tasks.json found. Using a default task.")
        tasks = [Task(id="task_0", description="Look at the homepage and tell me what the site is about.", 
                     complexity=1, required_steps=["Navigate to home"])]

    # 3. Run Agent
    try:
        await env.start()
        for task in tasks[:1]: # Just run first task for verification
            result = await runner.run_task(output_dir, task, max_steps=10)
            print(f"\n--- Episode Result ---")
            print(f"Success: {result.success}")
            print(f"Steps: {result.steps}")
            print(f"Total Reward: {result.total_reward}")
            print(f"Trajectory saved to: {result.trajectory.website_dir if result.trajectory else 'N/A'}")
            
    finally:
        await env.stop()

if __name__ == "__main__":
    asyncio.run(main())
