
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

async def main():
    topic = "basic_math_calculator"
    output_dir = "output/e2e_calc_test"
    
    print(f"🚀 Starting E2E Generation for: {topic}")
    
    # Initialize LLM with the remote model
    llm = CustomLLMProvider(
        base_url="http://10.166.75.190:8000/v1",
        model="/volume/pt-train/models/DeepSeek-V3.1"
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
    
    # Initialize Async Pipeline with 1 concurrency for maximum stability
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
        max_concurrency=1
    )
    
    print("Running pipeline...")
    try:
        await pipeline.run(topic, output_dir)
        print(f"✅ E2E Generation Successful! Output in {output_dir}")
        
        # Verify critical files exist
        critical_files = ["index.html", "logic.js", "evaluator.js", "tasks.json"]
        for f in critical_files:
            path = os.path.join(output_dir, f)
            if os.path.exists(path):
                print(f"  [FOUND] {f} ({os.path.getsize(path)} bytes)")
            else:
                print(f"  [MISSING] {f}")
                
    except Exception as e:
        print(f"❌ Generation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
