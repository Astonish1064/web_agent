
import asyncio
import os
import sys

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import CustomLLMProvider
from src.generators.task_generator import LLMTaskGenerator
from src.generators.interface_designer import LLMInterfaceDesigner
from src.generators.architecture_designer import LLMArchitectDesigner
from src.generators.data_generator import LLMDataGenerator
from src.generators.backend_generator import LLMBackendGenerator
from src.generators.page_designer import LLMPageDesigner
from src.generators.frontend_generator import LLMFrontendGenerator
from src.generators.instrumentation_generator import LLMInstrumentationGenerator
from src.generators.evaluator_generator import LLMEvaluatorGenerator

from src.async_pipeline import AsyncWebGenPipeline

async def main():
    topic = "online_bookstore"
    output_dir = "output/deepseek_v3_test"
    
    print(f"🚀 Starting Async Generation for: {topic}")
    
    # Initialize LLM
    llm = CustomLLMProvider()
    
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
    
    # Initialize Async Pipeline
    pipeline = AsyncWebGenPipeline(
        task_gen,
        interface_designer,
        arch_designer,
        data_gen,
        backend_gen,
        page_designer,
        frontend_gen,
        instr_gen,
        evaluator_gen
    )
    
    # Run
    import time
    start = time.perf_counter()
    
    await pipeline.run(topic, output_dir)
    
    end = time.perf_counter()
    print(f"✅ Generation Complete in {end - start:.2f}s!")
    print(f"📂 Output directory: {output_dir}")

if __name__ == "__main__":
    asyncio.run(main())
