import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, call
from src.interfaces import ILLMProvider
# will fail here because with_retry is not implemented yet
try:
    from src.utils import with_retry
except ImportError:
    # Allow test collection to proceed so we start Red
    with_retry = lambda **ops: lambda func: func 


class MockLLM(ILLMProvider):
    def __init__(self):
        self.prompt = Mock()
        self.prompt_json = Mock()
    
    def prompt(self, text):
        return self.prompt(text)
        
    def prompt_json(self, text):
        return self.prompt_json(text)

def test_retry_on_empty_result():
    """Test that function retries when result is None/Empty."""
    mock_llm = MockLLM()
    # Sequence: Return None (fail), Return None (fail), Return "Success"
    mock_llm.prompt.side_effect = [None, None, '{"data": "success"}']
    
    @with_retry(max_retries=3)
    def generate_something(llm):
        response = llm.prompt("test")
        if not response:
            return None
        return response

    result = generate_something(mock_llm)
    
    assert result == '{"data": "success"}'
    assert mock_llm.prompt.call_count == 3

def test_max_retries_limit():
    """Test that function gives up after max_retries."""
    mock_llm = MockLLM()
    # Always fail
    mock_llm.prompt.return_value = None
    
    @with_retry(max_retries=2)
    def generate_something(llm):
        return llm.prompt("test")

    result = generate_something(mock_llm)
    
    assert result is None
    # Initial call + 2 retries = 3 calls total
    assert mock_llm.prompt.call_count == 3

def test_retry_on_exception():
    """Test that function retries when an exception is raised."""
    mock_llm = MockLLM()
    # Sequence: Raise Error, Raise Error, Return Success
    mock_llm.prompt.side_effect = [Exception("LLM Error"), Exception("Timeout"), "Success"]
    
    @with_retry(max_retries=3)
    def generate_something(llm):
        return llm.prompt("test")

    result = generate_something(mock_llm)
    
    assert result == "Success"
    assert mock_llm.prompt.call_count == 3
