import os
import sys
import shutil
import json
from dataclasses import dataclass

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.generators.openhands_resolver import OpenHandsResolver
from src.llm import CustomLLMProvider

def test_openhands_resolver():
    # Setup test workspace
    test_dir = os.path.join(os.getcwd(), "test_openhands_workspace")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # Create a broken scenario
    # logic.js exists but is missing a function that frontend expects
    with open(os.path.join(test_dir, "logic.js"), "w") as f:
        f.write("""
class WebsiteSDK {
    constructor() {
        console.log("SDK initialized");
    }
    // Missing 'getData' function
}
window.WebsiteSDK = new WebsiteSDK();
""")
    
    with open(os.path.join(test_dir, "index.html"), "w") as f:
        f.write("""
<!DOCTYPE html>
<html>
<body>
    <button onclick="window.WebsiteSDK.getData()">Click Me</button>
    <script src="logic.js"></script>
</body>
</html>
""")

    llm = CustomLLMProvider(
        base_url="http://10.166.90.27:8000/v1",
        model="/volume/pt-train/models/DeepSeek-V3.1"
    )
    
    resolver = OpenHandsResolver(llm, test_dir)
    
    errors = ["[index.html] JS Error: Uncaught TypeError: window.WebsiteSDK.getData is not a function"]
    spec_context = {
        "tasks": [{"id": "t1", "description": "Get data on click"}],
        "interfaces": [{"name": "getData"}]
    }
    
    print("🚀 Testing OpenHands Resolver (Autonomous Mode)...")
    try:
        success = resolver.resolve(errors, spec_context)
        if success:
            print("\n✅ Verification Successful! OpenHands claims to have fixed the issue.")
            # Check if logic.js was modified
            with open(os.path.join(test_dir, "logic.js"), "r") as f:
                content = f.read()
                if "getData" in content:
                    print("📊 Confirmed: 'getData' was added to logic.js")
                else:
                    print("⚠️ Note: 'getData' not found in logic.js, may have fixed it in index.html or elsewhere.")
        else:
            print("\n❌ Verification Failed: OpenHands could not resolve the issue.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Execution Error: {e}")
    finally:
        # shutil.rmtree(test_dir)
        pass

if __name__ == "__main__":
    test_openhands_resolver()
