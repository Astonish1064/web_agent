
import asyncio
import os
import sys
import json

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import CustomLLMProvider
from src.generators.task_generator import LLMTaskGenerator, TaskConfig
from src.generators.interface_designer import LLMInterfaceDesigner
from src.generators.architecture_designer import LLMArchitectDesigner
from src.generators.data_generator import LLMDataGenerator
from src.generators.backend_generator import LLMBackendGenerator
from src.generators.page_designer import LLMPageDesigner
from src.generators.frontend_generator import LLMFrontendGenerator
from src.generators.instrumentation_generator import LLMInstrumentationGenerator
from src.generators.evaluator_generator import LLMEvaluatorGenerator

from src.async_pipeline import AsyncWebGenPipeline
from src.domain import WebsiteSpec

async def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "simple_todo_list"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output/deepseek_mini_test"
    
    print(f"🚀 Starting Mini Async Generation for: {topic}")
    
    # Initialize LLM with the remote model
    llm = CustomLLMProvider(
        base_url="https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47/v1",
        model="/volume/pt-train/models/GLM-4.7"
    )
    
    # Initialize Generators
    task_gen = LLMTaskGenerator(llm)
    interface_designer = LLMInterfaceDesigner(llm)
    arch_designer = LLMArchitectDesigner(llm)
    data_gen = LLMDataGenerator(llm)
    backend_gen = LLMBackendGenerator(llm)
    page_designer = LLMPageDesigner(llm)
    frontend_gen = LLMFrontendGenerator(llm)
    instr_gen = LLMInstrumentationGenerator(llm)
    evaluator_gen = LLMEvaluatorGenerator(llm)
    
    # Initialize Async Pipeline with 1 concurrency
    pipeline = AsyncWebGenPipeline(
        task_gen,
        interface_designer,
        arch_designer,
        data_gen,
        backend_gen,
        page_designer,
        frontend_gen,
        instr_gen,
        evaluator_gen,
        llm=llm,
        max_concurrency=1
    )
    
    # We will override _run_planning_phase to force a small architecture
    # but still use the real LLM logic
    
    print("Running pipeline...")
    try:
        await pipeline.run(topic, output_dir)
        print("✅ Mini Generation Successful!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Generation Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
