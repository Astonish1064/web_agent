from src.utils import clean_json_response, clean_code_response
import json

# Simulated LLM response (based on logic.js content)
response = """```json
{
  "code": "const foo = 'bar';"
}
```"""

print(f"Original Response:\n{response}")
print("-" * 20)

# Test clean_json_response
parsed = clean_json_response(response)
print(f"Parsed JSON: {parsed}")
if parsed:
    print(f"Extracted Code: {parsed.get('code')}")
else:
    print("JSON Parsing FAILED")

print("-" * 20)

# Test clean_code_response
cleaned_code = clean_code_response(response)
print(f"Cleaned Code: {cleaned_code}")
