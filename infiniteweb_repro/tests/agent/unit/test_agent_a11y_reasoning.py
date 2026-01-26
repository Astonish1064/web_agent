import pytest
from unittest.mock import MagicMock, AsyncMock
from src.agent.agents.llm_agent import LLMWebAgent
from src.agent.domain import Observation, Action
from src.domain import Task

@pytest.mark.asyncio
async def test_agent_decide_uses_a11y_tree():
    llm = MagicMock()
    agent = LLMWebAgent(llm)
    
    # Mock LLM response
    llm.prompt_json.return_value = {
        "reasoning": "I need to click the search button",
        "action": {"type": "click", "target": "[button] 'Search'"}
    }
    
    obs = Observation(
        url="http://localhost/",
        page_title="Home",
        screenshot=b"",
        dom_tree="<html>...</html>",
        a11y_tree="[RootWebArea] ''\n  [button] 'Search'",
        instrumentation_state={}
    )
    
    task = Task(id="1", description="Search for books", complexity=1, required_steps=[])
    
    action = await agent.decide(obs, task, [])
    
    assert action.type == "click"
    assert action.target == "[button] 'Search'"
    
    # Verify that the prompt sent to LLM contained the A11y Tree
    prompt_sent = llm.prompt_json.call_args[0][0]
    assert "Accessibility Tree (Recommended):" in prompt_sent
    assert "[button] 'Search'" in prompt_sent
