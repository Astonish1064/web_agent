import re
import os

LOGIC_FILE = "/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro/output/deepseek_v31_system_test/logic.js"
TEST_FILE = "/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro/output/deepseek_v31_system_test/backend_tests.js"

def clean_content(content):
    # Remove specific hallucinated phrases
    content = content.replace("极客时间", "")
    content = content.replace("极", "")
    
    # Fix potential syntax errors resulting from removal
    # e.g. "price: ," -> "price: 0,"
    content = re.sub(r'price:\s*,', 'price: 0,', content)
    content = re.sub(r'price:\s*}', 'price: 0}', content)
    
    # Fix "cores: 14," where "14" was "14"
    # The removal of "极客时间" might leave "cores: 14" which is fine.
    
    # Fix "wattage 650" -> "wattage: 650" if colon was eaten (unlikely if '极客时间' was just inserted)
    # But look at line 74 in logic.js: "wattage极客时间 650". 
    # Removal gives "wattage 650". This IS a syntax error (missing colon).
    content = re.sub(r'(\w+)\s+(\d+)', r'\1: \2', content) # conservative? 
    # Actually "wattage 650" inside an object needs a colon.
    # regex for object property missing colon: "key value" -> "key: value"
    # valid js: "key: value", "method()", "async method()"
    # We target specific known issues.
    
    content = re.sub(r'wattage\s+(\d+)', r'wattage: \1', content)
    content = re.sub(r'memory\s+(\d+)', r'memory: \1', content)
    
    return content

def process_file(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    cleaned = clean_content(original)
    
    if original != cleaned:
        print(f"Fixing corruption in {filepath}...")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned)
    else:
        print(f"No corruption found in {filepath}.")

process_file(LOGIC_FILE)
process_file(TEST_FILE)
