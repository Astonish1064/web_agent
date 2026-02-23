
import sys
import os
import json
import asyncio

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import CustomLLMProvider
from src.generators.frontend_generator import LLMFrontendGenerator
from src.domain import GenerationContext, WebsiteSpec, PageSpec
from src.generators.architecture_designer import Architecture

async def main():
    print("🚀 Starting Framework Generation Isolation Test")
    
    # Initialize LLM
    llm = CustomLLMProvider(
        base_url="https://console.siflow.cn/siflow/zhuoguang/skyinfer/yxing/dpskv32-tp8dp1-h20-service/v1",
        model="DeepSeek-V3.2"
    )
    
    frontend_gen = LLMFrontendGenerator(llm)
    
    # Mock Spec
    spec = WebsiteSpec(seed="gaming_pc_configurator")
    
    # Mock Architecture
    arch = Architecture(
        pages=[],
        header_links=[{"text": "Home", "url": "index.html"}],
        footer_links=[{"text": "Privacy", "url": "privacy.html"}]
    )
    
    print("mock arch created, calling generate_framework...")
    
    try:
        framework = frontend_gen.generate_framework(spec, arch)
        print(f"✅ Framework Generated!")
        print(f"HTML Length: {len(framework.html)}")
        print(f"CSS Length: {len(framework.css)}")
        print("HTML Content Preview:")
        print(framework.html[:500])
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
