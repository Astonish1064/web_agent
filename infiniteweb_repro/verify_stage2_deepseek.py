
import asyncio
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import CustomLLMProvider
from src.generators.frontend_generator import LLMFrontendGenerator
from src.domain import WebsiteSpec, PageSpec
from src.generators.architecture_designer import Architecture, PageArchitecture

async def main():
    print(f"🎨 Verification Stage 2: Page Generation")
    llm = CustomLLMProvider(
        base_url="http://10.166.75.190:8000/v1",
        model="/volume/pt-train/models/DeepSeek-V3.1"
    )
    
    frontend_gen = LLMFrontendGenerator(llm)
    spec = WebsiteSpec(seed="mini_blog")
    # Mock some architecture data using dataclasses
    p1 = PageArchitecture(
        name="Home", 
        filename="index.html", 
        assigned_interfaces=["getPosts", "searchPosts"],
        incoming_params=[], 
        outgoing_connections=[]
    )
    arch = Architecture(
        all_pages=[{"name": "Home", "filename": "index.html"}],
        pages=[p1],
        header_links=[{"text": "Home", "url": "index.html"}],
        footer_links=[]
    )
    spec.architecture = arch
    
    # 1. Framework
    print("🏠 Generating Framework...")
    framework = await asyncio.to_thread(frontend_gen.generate_framework, spec, arch)
    print(f"✅ Framework Generated ({len(framework.html)} chars HTML, {len(framework.css)} chars CSS)")
    
    # 2. Page HTML
    print("📄 Generating index.html...")
    page_spec = PageSpec(name="Home", filename="index.html", description="The main landing page.")
    page_design = MagicMock() # We'll just mock it or skip since prompt uses keys
    # To keep it simple, we'll pass a dict if the generator expects it
    html = await asyncio.to_thread(frontend_gen.generate_html, spec, page_spec, {}, arch.pages[0], framework)
    print(f"✅ HTML Generated ({len(html)} chars)")
    print("\nSAMPLE HTML START:")
    print(html[:500] + "...")

from unittest.mock import MagicMock
if __name__ == "__main__":
    asyncio.run(main())
