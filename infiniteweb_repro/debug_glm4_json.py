
import asyncio
import os
import sys
import json

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import CustomLLMProvider
from src.generators.frontend_generator import LLMFrontendGenerator
from src.domain import GenerationContext, PageSpec, Framework

async def debug_glm4_html():
    base_url = "https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47-tool-fork/v1"
    llm = CustomLLMProvider(
        base_url=base_url,
        model="glm-4"
    )
    
    gen = LLMFrontendGenerator(llm)
    
    # Load intermediate samples to mock input
    intermediates_dir = "output/glm4_verification/intermediates"
    
    # Mock some basic data
    with open(os.path.join(intermediates_dir, "1_tasks.json"), "r") as f:
        tasks = json.load(f)
    
    page = PageSpec(name="Home", filename="index.html", description="The main landing page.")
    
    # Mocking framework
    framework = Framework(html="<header>Header</header><main id='content'></main><footer>Footer</footer>", css="")
    
    # Mocking designs
    with open(os.path.join(intermediates_dir, "page_index.html_1_design.json"), "r") as f:
        page_design = json.load(f)
    
    with open(os.path.join(intermediates_dir, "page_index.html_2_layout.json"), "r") as f:
        page_arch = json.load(f)

    # Wrap in simple objects as generator expects them to have __dict__
    class SimpleObj:
        def __init__(self, d): self.__dict__.update(d)
        
    print("🚀 Attempting to reproduce GLM-4 HTML generation failure...")
    html = await asyncio.to_thread(
        gen.generate_html,
        SimpleObj({"seed": "Solar Dashboard", "data_models": []}),
        page,
        SimpleObj(page_design),
        SimpleObj(page_arch),
        framework
    )
    
    if html:
        print(f"✅ Success! Generated {len(html)} chars.")
    else:
        print("❌ Failed. Check stdout for [DEBUG] lines and json_failure_debug.log")

if __name__ == "__main__":
    asyncio.run(debug_glm4_html())
