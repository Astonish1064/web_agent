import os
import sys

# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from src.llm import CustomLLMProvider

def test_connection(name, url):
    print(f"\n🔍 Testing {name} at {url}...")
    try:
        llm = CustomLLMProvider(base_url=url)
        print(f"✅ Success! Connected to model: {llm.model}")
        
        # Quick test prompt
        response = llm.prompt("Say 'Hello from " + name + "!' briefly.")
        print(f"💬 Response: {response.strip()}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to {name}: {e}")
        return False

if __name__ == "__main__":
    gen_url = "http://172.16.152.159:8000/v1"
    plan_url = "http://10.166.97.108:8000/v1"
    
    s1 = test_connection("Gen Server (Qwen32B)", gen_url)
    s2 = test_connection("Plan Server (DeepSeek-V3.1)", plan_url)
    
    if s1 and s2:
        print("\n✨ All systems go! You can now run the pipeline with:")
        print(f"python main.py --seed online_bookstore --gen-url {gen_url} --plan-url {plan_url}")
    else:
        print("\n⚠️ Some servers are unreachable. Check if vLLM is running on both nodes.")
