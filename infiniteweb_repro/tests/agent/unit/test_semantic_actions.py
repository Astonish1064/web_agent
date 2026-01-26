import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agent.environments.action_executor import ActionExecutor
from src.agent.domain import Action

@pytest.mark.asyncio
async def test_click_semantic_target():
    executor = ActionExecutor()
    page = MagicMock()
    
    # Action with semantic target
    action = Action(type="click", target="[button] 'Search'")
    
    # We expect ActionExecutor to parse "[button] 'Search'"
    # and call page.get_by_role("button", name="Search")
    
    mock_locator = MagicMock()
    page.get_by_role.return_value = mock_locator
    mock_locator.click = AsyncMock()
    
    success = await executor.execute(page, action)
    
    assert success is True
    page.get_by_role.assert_called_once_with("button", name="Search")
    mock_locator.click.assert_called_once()

@pytest.mark.asyncio
async def test_type_semantic_target():
    executor = ActionExecutor()
    page = MagicMock()
    
    action = Action(type="type", target="[textbox] 'Email'", value="test@example.com")
    
    mock_locator = MagicMock()
    page.get_by_role.return_value = mock_locator
    mock_locator.fill = AsyncMock()
    
    success = await executor.execute(page, action)
    
    assert success is True
    page.get_by_role.assert_called_once_with("textbox", name="Email")
    mock_locator.fill.assert_called_once_with("test@example.com", timeout=5000)

@pytest.mark.asyncio
async def test_fallback_to_selector():
    executor = ActionExecutor()
    page = MagicMock()
    
    # Traditional CSS selector
    action = Action(type="click", target="#search-btn")
    
    page.click = AsyncMock()
    
    success = await executor.execute(page, action)
    
    assert success is True
    page.click.assert_called_once_with("#search-btn", timeout=5000)
