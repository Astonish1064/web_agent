
import asyncio
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import CustomLLMProvider
from src.generators.task_generator import LLMTaskGenerator, TaskConfig
from src.generators.interface_designer import LLMInterfaceDesigner
from src.generators.architecture_designer import LLMArchitectDesigner
from src.domain import WebsiteSpec

async def main():
    print(f"🏗️ Verification Stage 1: Planning and Architecture")
    llm = CustomLLMProvider(
        base_url="http://10.166.75.190:8000/v1",
        model="/volume/pt-train/models/DeepSeek-V3.1"
    )
    
    spec = WebsiteSpec(seed="mini_blog")
    
    # 1. Tasks
    print("📋 Generating Tasks...")
    task_gen = LLMTaskGenerator(llm)
    spec.tasks = await asyncio.to_thread(task_gen.generate, spec.seed, TaskConfig(website_type=spec.seed))
    print(f"✅ Generated {len(spec.tasks)} tasks.")
    
    # 2. Interfaces
    print("🔌 Designing Interfaces...")
    interface_designer = LLMInterfaceDesigner(llm)
    spec.interfaces = await asyncio.to_thread(interface_designer.design, spec)
    print(f"✅ Designed {len(spec.interfaces)} interfaces.")
    
    # 3. Architecture
    print("🏗️ Designing Architecture...")
    arch_designer = LLMArchitectDesigner(llm)
    spec.architecture = await asyncio.to_thread(arch_designer.design, spec)
    print(f"✅ Designed architecture with {len(spec.architecture.pages)} pages.")
    
    for p in spec.architecture.pages:
        print(f"    - {p.filename}: {p.name}")

if __name__ == "__main__":
    asyncio.run(main())
