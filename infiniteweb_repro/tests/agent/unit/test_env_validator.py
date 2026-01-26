import pytest
import os
import shutil
import tempfile
import asyncio
from src.agent.environments.env_validator import EnvironmentHealthChecker
from unittest.mock import MagicMock

@pytest.fixture
def temp_output_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)

@pytest.mark.asyncio
async def test_validate_backend_success(temp_output_dir):
    # Setup healthy logic.js and test.js
    logic_js = "class BusinessLogic { add(a, b) { return a + b; } }\nmodule.exports = BusinessLogic;"
    test_js = """
const BusinessLogic = require('./logic.js');
const logic = new BusinessLogic();
if (logic.add(1, 2) !== 3) throw new Error('Test failed');
console.log('Test Passed');
"""
    with open(os.path.join(temp_output_dir, "logic.js"), "w") as f:
        f.write(logic_js)
    with open(os.path.join(temp_output_dir, "backend_tests.js"), "w") as f:
        f.write(test_js)

    checker = EnvironmentHealthChecker()
    success, error = await checker.validate_backend(temp_output_dir)
    assert success is True
    assert error is None

@pytest.mark.asyncio
async def test_validate_backend_failure(temp_output_dir):
    # Setup faulty logic.js
    logic_js = "class BusinessLogic { add(a, b) { return a - b; } }\nmodule.exports = BusinessLogic;"
    test_js = """
const BusinessLogic = require('./logic.js');
const logic = new BusinessLogic();
if (logic.add(1, 2) !== 3) throw new Error('Assertion Failed: 1+2 should be 3');
"""
    with open(os.path.join(temp_output_dir, "logic.js"), "w") as f:
        f.write(logic_js)
    with open(os.path.join(temp_output_dir, "backend_tests.js"), "w") as f:
        f.write(test_js)

    checker = EnvironmentHealthChecker()
    success, error = await checker.validate_backend(temp_output_dir)
    assert success is False
    assert "Assertion Failed" in error

@pytest.mark.asyncio
async def test_validate_frontend_page_error(temp_output_dir):
    # Setup page with JS error
    index_html = """
    <html>
        <body><h1>Test</h1><script>throw new Error('Frontend Crash');</script></body>
    </html>
    """
    with open(os.path.join(temp_output_dir, "index.html"), "w") as f:
        f.write(index_html)

    checker = EnvironmentHealthChecker()
    # Mocking playwright environment or using a real one in headless mode
    # For unit test, we might want to keep it simple or use a real headless run
    success, error = await checker.validate_frontend(temp_output_dir, "index.html")
    assert success is False
    assert "Frontend Crash" in error
