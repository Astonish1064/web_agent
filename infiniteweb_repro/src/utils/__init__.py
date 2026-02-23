import json
import re
import functools
import time
import random

def clean_json_response(response: str):
    """
    Extracts and parses JSON from an LLM response.
    Specifically designed to handle malformed JSON where the LLM might:
    1. Start with raw HTML then switch to JSON
    2. Include unescaped quotes/newlines
    3. Return a flat map of files
    """
    if not response:
        return None
        
    text = response.strip()
    
    # Try to find JSON block in markdown
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        text = match.group(1)
    
    # Pre-cleaning for literal newlines in quotes
    def _repair_json(s):
        parts = re.split(r'("(?:\\.|[^"\\])*")', s)
        for idx in range(1, len(parts), 2):
            parts[idx] = parts[idx].replace('\n', '\\n').replace('\r', '\\r')
        s = "".join(parts)
        s = re.sub(r',\s*([}\]])', r'\1', s)
        return s


    # 1. Try standard/repaired JSON load first
    try:
        return json.loads(text, strict=False)
    except:
        try:
            return json.loads(_repair_json(text), strict=False)
        except:
            pass

    # 2. Robust Multi-Pass Extraction (The "v10 Production Fix")
    file_map = {}
    key_pattern = r'"([^"]+\.html)"\s*:\s*"'
    keys_found = list(re.finditer(key_pattern, text))
    
    if keys_found:
        # Pass 1: Handle the text BEFORE the first identified key (often raw index.html)
        prefix = text[:keys_found[0].start()].strip()
        if "<!DOCTYPE html>" in prefix or "<html>" in prefix.lower():
            # If the prefix is significant HTML, treat it as index.html
            file_map["index.html"] = prefix
        
        # Pass 2: Extract identified keys
        for i in range(len(keys_found)):
            start_match = keys_found[i]
            fname = start_match.group(1)
            content_start = start_match.end()
            
            if i + 1 < len(keys_found):
                content_end = keys_found[i+1].start()
            else:
                content_end = len(text)
            
            raw_val = text[content_start:content_end].strip()
            
            # Heuristic: Find the true closing quote.
            # It's usually the one followed by a comma and the next key, or the final brace.
            # We look for a pattern like " followed by some whitespace and then , or }
            match_end = re.search(r'"\s*(?:,|\s*})?\s*$', raw_val)
            if match_end:
                raw_val = raw_val[:match_end.start()]
            else:
                # Fallback: if we don't find the pattern, it might be the last quote
                # but only if it's near the end of the raw_val
                last_quote_idx = raw_val.rfind('"')
                if last_quote_idx > len(raw_val) - 10:
                    raw_val = raw_val[:last_quote_idx]
            
            content = raw_val.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
            # Clean accidental 'n' prefix from multi-line strings
            if content.strip().startswith('n') and '<' not in content[:10]:
                content = content.strip()[1:].strip()
            
            file_map[fname] = content
        
        if file_map:
            return file_map

    # 3. Fallback for raw HTML (Single File)
    if "<!DOCTYPE html>" in response or "<html>" in response.lower():
        raw_content = clean_code_response(response)
        return {"index.html": raw_content or response}
        
    # 4. Fallback for other blocks
    if "```" in response or "{" in response:
        raw_content = clean_code_response(response)
        if raw_content:
            return {"__raw__": raw_content}

    return None

def clean_code_response(response: str) -> str:
    if not response: return ""
    text = response.strip()
    pattern = r"```(?:\w+)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match: text = match.group(1).strip()
    if text.startswith("```"): text = re.sub(r"^```(?:\w+)?\n?", "", text)
    if text.endswith("```"): text = re.sub(r"n?```$", "", text)
    return text.strip()

def with_retry(max_retries=5, delay=1.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if result is not None: return result
                except Exception as e:
                    last_exception = e
                    print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    time.sleep(delay * (2 ** attempt) + random.uniform(0, 1))
            return None
        return wrapper
    return decorator
