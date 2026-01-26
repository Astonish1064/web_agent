import pytest
import os
from unittest.mock import MagicMock
from src.agent.environments.playwright_env import PlaywrightEnvironment
from src.agent.agents.llm_agent import LLMWebAgent
from src.domain import Task
from src.agent.domain import Action

@pytest.mark.asyncio
async def test_agent_a11y_end_to_end():
    # 1. Setup mock website
    website_dir = "tests/system_a11y_test"
    os.makedirs(website_dir, exist_ok=True)
    with open(os.path.join(website_dir, "index.html"), "w") as f:
        f.write("""
        <html>
            <body>
                <h1>Book Store</h1>
                <button id="real-search-id">Search Books</button>
                <div id="result" style="display:none">Search Results Found!</div>
                <script>
                    document.getElementById('real-search-id').onclick = () => {
                        document.getElementById('result').style.display = 'block';
                    }
                </script>
            </body>
        </html>
        """)
    
    # 2. Setup Agent with Mock LLM
    llm = MagicMock()
    agent = LLMWebAgent(llm)
    
    # LLM will decide to click the semantic target
    llm.prompt_json.return_value = {
        "reasoning": "I see the search button in the A11y tree and will click it.",
        "action": {"type": "click", "target": "[button] 'Search Books'"}
    }
    
    env = PlaywrightEnvironment(headless=True)
    try:
        task = Task(id="test_task", description="Click the search button", complexity=1, required_steps=[])
        
        # Step 1: Reset environment
        obs = await env.reset(website_dir, task)
        assert "[button] 'Search Books'" in obs.a11y_tree
        
        # Step 2: Agent Decides
        action = await agent.decide(obs, task, [])
        assert action.target == "[button] 'Search Books'"
        
        # Step 3: Execute in environment
        obs, reward, done, info = await env.step(action)
        
        # Step 4: Verify result (the hidden div should now be visible)
        is_visible = await env.page.is_visible("#result")
        assert is_visible is True
        print("\nEnd-to-end A11y action successful!")
        
    finally:
        await env.stop()
