import pytest
import os
from src.agent.environments.playwright_env import PlaywrightEnvironment
from src.domain import Task

@pytest.mark.asyncio
async def test_a11y_tree_capture_integration():
    # Setup - we need a real website directory
    # Let's use bookstore_v3 if it exists, otherwise a simple mock
    website_dir = "tests/mock_a11y_site"
    os.makedirs(website_dir, exist_ok=True)
    with open(os.path.join(website_dir, "index.html"), "w") as f:
        f.write("<html><body><h1>Test Site</h1><button>Click Me</button></body></html>")
    
    env = PlaywrightEnvironment(headless=True)
    try:
        task = Task(id="test_task", description="Test a11y", complexity=1, required_steps=[])
        obs = await env.reset(website_dir, task)
        
        # Explicitly wait for an element to ensure A11y tree is ready
        await env.page.wait_for_selector("h1")
        # Recapture observation to get the updated A11y tree
        obs = await env._capture_observation()
        
        print("\nDEBUG: Full A11y Tree Output:")
        print(obs.a11y_tree)
        
        assert obs.a11y_tree is not None
        assert "[heading] 'Test Site'" in obs.a11y_tree
        assert "[button] 'Click Me'" in obs.a11y_tree
        
        print("\nCaptured A11y Tree:\n", obs.a11y_tree)
        
    finally:
        await env.stop()
