
import asyncio
from src.llm import CustomLLMProvider

async def main():
    print(f"📡 Testing LLM Connectivity on 10.166.75.190...")
    llm = CustomLLMProvider(
        base_url="http://10.166.75.190:8000/v1",
        model="/volume/pt-train/models/DeepSeek-V3.1"
    )
    
    # Test 1: Simple Prompt
    resp = llm.prompt("Hello, who are you? Please keep it very short.")
    print(f"✅ Text Response: {resp}")
    
    # Test 2: JSON Prompt
    json_resp = llm.prompt_json("Generate a JSON object with a key 'test' and value 'success'")
    print(f"✅ JSON Response: {json_resp}")

if __name__ == "__main__":
    asyncio.run(main())
