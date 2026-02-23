import asyncio
import os
import sys
import json

# Add current directory to path so src is treated as a package
sys.path.append(os.getcwd())

from src.llm import CustomLLMProvider
from src.generators.frontend_generator import LLMFrontendGenerator
from src.domain import Task, WebsiteSpec

async def test_live_frontend_extraction():
    print("🚀 Starting Live LLM Integration Test...")
    
    # 1. Setup LLM (using the same config as the pipeline)
    base_url = "https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47-tool-fork/v1"
    llm = CustomLLMProvider(base_url=base_url, model="glm-4")
    frontend_gen = LLMFrontendGenerator(llm)
    
    # 2. Mock minimal inputs
    task = Task(id="test_task", name="Test Home", description="Search for a book and add to cart", steps=["Search", "Add"])
    spec = WebsiteSpec(seed="online_bookstore", interfaces=[], data_models=[])
    
    print("📡 Calling LLM for frontend implementation (this might take a few seconds)...")
    
    # 3. Call the generator (this triggers the real LLM and our clean_json_response)
    try:
        pages = await asyncio.to_thread(frontend_gen.implement_task_view, task, "// Test logic", spec)
        
        print("\n📊 Extraction Result:")
        if isinstance(pages, dict):
            print(f"✅ Success! Extracted {len(pages)} keys.")
            for filename in pages.keys():
                content_len = len(pages[filename])
                print(f"   - {filename}: {content_len} bytes")
                if content_len > 0:
                    snippet = pages[filename][:100].replace('\n', ' ')
                    print(f"     Preview: {snippet}...")
            
            # Verify if we got the expected files (usually index.html)
            if any(k.endswith(".html") for k in pages.keys()):
                print("\n🎉 LIVE EXTRACTION VERIFIED: Real LLM output was correctly parsed into files.")
            else:
                print("\n⚠️  No .html files found in the parsed output.")
        else:
            print(f"❌ Failed! Output is not a dict: {type(pages)}")
            print(f"Raw response: {pages}")

    except Exception as e:
        print(f"💥 Error during live test: {e}")

if __name__ == "__main__":
    asyncio.run(test_live_frontend_extraction())
