import json
import re
import functools
import time

def clean_json_response(response: str):
    """
    Extracts and parses JSON from an LLM response.
    Handles markdown code blocks (```json ... ```) and raw JSON.
    Returns parsed object (dict or list) or None if parsing fails.
    """
    if not response:
        return None
        
    text = response.strip()
    
    # Try to find JSON block in markdown
    # Match ```json ... ``` or ``` ... ```
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        text = match.group(1)
    
    # If no markdown, or after extraction, try to find the outer JSON structure
    # This helps if there is conversational text around the JSON
    # Find first '{' or '['
    first_brace = text.find('{')
    first_bracket = text.find('[')
    
    start_idx = -1
    end_idx = -1
    
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        # Starts with object
        start_idx = first_brace
        end_idx = text.rfind('}')
    elif first_bracket != -1:
        # Starts with list
        start_idx = first_bracket
        end_idx = text.rfind(']')
        
    if start_idx != -1 and end_idx != -1:
        text = text[start_idx : end_idx + 1]
        
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

def clean_code_response(response: str) -> str:
    """
    Extracts code from a markdown block if present.
    """
    if not response:
        return ""
        
    text = response.strip()
    
    # Check for markdown block
    # Matches ```language ... ``` or ``` ... ```
    pattern = r"```(?:\w+)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
            
    return text

import random # Added for jitter

def with_retry(max_retries=5, delay=1.0):
    """
    Decorator to retry generation on failure (None result) or exception.
    
    Args:
        max_retries (int): Maximum number of retries.
        delay (int): Base delay in seconds between retries.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            # Try initial call + retries
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    # If result is not None, return it (empty list is valid)
                    if result is not None:
                        return result
                    # If result is None, count as failure and retry
                except Exception as e:
                    last_exception = e
                    print(f"Attempt {attempt + 1} failed with error: {e}")
                
                if attempt < max_retries:
                    # Exponential backoff with Jitter
                    sleep_time = delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
            
            # If we exhausted all retries
            if last_exception:
                print(f"Max retries ({max_retries}) reached. Last error: {last_exception}")
                return None
            
            print(f"Max retries ({max_retries}) reached. Result was empty.")
            return None
            
        return wrapper
    return decorator
