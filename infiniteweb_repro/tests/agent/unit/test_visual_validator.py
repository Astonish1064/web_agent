import pytest
import os
import shutil
import tempfile
import asyncio
from unittest.mock import MagicMock, patch
from src.agent.environments.env_validator import VisualValidator, EnvironmentHealthChecker
from src.interfaces import ILLMProvider

@pytest.fixture
def temp_output_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)

@pytest.mark.asyncio
async def test_visual_validator_success(temp_output_dir):
    # Setup mock LLM
    mock_llm = MagicMock(spec=ILLMProvider)
    mock_llm.prompt_json.return_value = {
        "score": 9,
        "pass": True,
        "feedback": "Perfect layout",
        "visual_bugs": []
    }
    
    # Create fake screenshot
    screenshot_path = os.path.join(temp_output_dir, "test.png")
    with open(screenshot_path, "wb") as f:
        f.write(b"fake_image_data")
        
    validator = VisualValidator(mock_llm)
    result = await validator.validate(screenshot_path, "test_seed", "index.html", "Test Page")
    
    assert result["score"] == 9
    assert result["pass"] is True
    assert mock_llm.prompt_json.call_count == 1

@pytest.mark.asyncio
async def test_environment_checker_screenshot(temp_output_dir):
    # Setup page
    index_html = "<html><body><h1>Welcome to the Multimodal Validation Test Page</h1><p>This is a test page designed to have enough content to pass the richness heuristic check in our EnvironmentHealthChecker. It needs to be at least 50 characters long to avoid the richness error. Now it should be long enough.</p></body></html>"
    with open(os.path.join(temp_output_dir, "index.html"), "w") as f:
        f.write(index_html)
        
    checker = EnvironmentHealthChecker()
    screenshot_path = os.path.join(temp_output_dir, "snapshot.png")
    
    success, error = await checker.validate_frontend(
        temp_output_dir, "index.html", screenshot_path=screenshot_path
    )
    
    assert success is True, f"Validation failed with error: {error}"
    assert os.path.exists(screenshot_path)
    assert os.path.getsize(screenshot_path) > 0
