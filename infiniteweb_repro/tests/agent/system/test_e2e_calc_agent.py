import pytest
import asyncio
import os
from src.agent.environments.playwright_env import PlaywrightEnvironment
from src.agent.agents.llm_agent import LLMWebAgent
from src.llm import CustomLLMProvider

@pytest.mark.asyncio
async def test_e2e_calc_budget():
    """
    Test the agent interacting with the generated calculator site.
    Ensures that A11y tree observation and semantic actions work on real generated components.
    """
    from src.domain import Task
    
    env = PlaywrightEnvironment(headless=True)
    try:
        # Path to the generated site
        website_dir = os.path.abspath("output/e2e_calc_test")
        
        # Create a dummy task object
        task = Task(
            id="calc_task",
            description=(
                "Navigate to the Budget Calculator. "
                "Calculate a budget with: "
                "Total Monthly Income: $5000, "
                "Savings: 20%, "
                "Housing: 30%, "
                "Food: 20%, "
                "Transportation: 10%, "
                "Entertainment: 10%, "
                "Other: 10%. "
                "Then click 'Calculate Budget' and verify the results."
            ),
            complexity=1,
            required_steps=[]
        )
        
        await env.reset(website_dir, task)
        
        # Custom LLM provider pointing to the remote DeepSeek model
        llm_provider = CustomLLMProvider()
        agent = LLMWebAgent(llm_provider)
        
        # Debug: Print console logs
        env.page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
        env.page.on("pageerror", lambda err: print(f"PAGE ERROR: {err.message}"))

        # 1. Page is already at homepage after reset
        try:
            await env.page.wait_for_selector("[data-action='selectCategory'][data-category-id='budget']", timeout=15000)
        except Exception as e:
            print(f"FAILED TO FIND BUDGET SELECTOR. Page Content:\n{await env.page.content()}")
            await env.page.screenshot(path="debug_index.png")
            raise e
        
        # 2. Run the agent to perform the task
        history = []
        max_steps = 15
        obs = env.get_observation()
        
        for i in range(max_steps):
            print(f"\n--- Step {i+1} ---")
            print(f"URL: {obs.url}")
            
            action = await agent.decide(obs, task, history)
            print(f"Agent Reasoning: {action.reasoning}")
            print(f"Action: {action.type}({action.target}, {action.value})")
            
            if action.type == "finish":
                print(f"Agent finished: {action.reasoning}")
                break
            elif action.type == "fail":
                print(f"Agent failed: {action.reasoning}")
                break
                
            obs, reward, done, info = await env.step(action)
            history.append(action)
            
            if done:
                print(f"Task completed (done=True). Final reward: {reward}")
                break
            
            # Wait for potential navigation or state changes
            await asyncio.sleep(1)
        
        # 3. Final Verification
        # Check if results display is visible and contains expected values
        is_visible = await env.page.is_visible("#results-display")
        assert is_visible, "Results display should be visible"
        
        content = await env.page.text_content("#results-display")
        assert "$5000.00" in content
        assert "20.0%" in content # Savings
        assert "30.0%" in content # Housing
        
    finally:
        await env.stop()

if __name__ == "__main__":
    asyncio.run(test_e2e_calc_budget())
