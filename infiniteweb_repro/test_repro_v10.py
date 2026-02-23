import sys
import os
import re

# Add current directory to path so src is treated as a package
sys.path.append(os.getcwd())

from src.utils import clean_json_response

def test_v10_debug():
    print("🧪 Debugging v10 Extraction...")
    v10_file = "/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro/output/mature_agents_v10_production/index.html"
    
    with open(v10_file, 'r') as f:
        content = f.read()

    print(f"📄 Content length: {len(content)}")
    print(f"📄 First 200 chars: {content[:200]!r}")
    
    # Check for the key pattern manually
    key_pattern = r'"([^"]+\.html)"\s*:\s*"'
    matches = list(re.finditer(key_pattern, content))
    print(f"🔍 Found {len(matches)} keys via regex:")
    for m in matches:
        print(f"   - {m.group(1)} at {m.start()}")

    result = clean_json_response(content)
    print(f"📊 Final Extracted Keys: {list(result.keys()) if result else 'None'}")

if __name__ == "__main__":
    test_v10_debug()
