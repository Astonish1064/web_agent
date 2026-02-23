
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
    topic = sys.argv[1] if len(sys.argv) > 1 else "ultra_modern_solar_dashboard"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output/glm4_verification"
    
    print(f"🚀 Starting Full Website Generation for: {topic}")
    print(f"📡 Using Endpoint: https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47-tool-fork")
    
    # Initialize LLM with the provided GLM-4 endpoint
    base_url = "https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47-tool-fork/v1"
    model_name = "glm-4"
    
    # [NEW] Configuration for OpenHands SDK
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_MODEL"] = f"openai/{model_name}" # OpenHands/LiteLLM prefix
    os.environ["LLM_API_KEY"] = "EMPTY"
    # Ensure sandbox runs locally for this repro
    os.environ["SANDBOX_TYPE"] = "local" 

    llm = CustomLLMProvider(
        base_url=base_url,
        model=model_name
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
    
    # Initialize Async Pipeline
    # Using max_concurrency=1 to ensure stability and clear logging
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
    
    print("🚦 Running optimized pipeline with Quality-First Architecture...")
    try:
        await pipeline.run(topic, output_dir)
        print(f"\n✅ Generation Successful! Output directory: {os.path.abspath(output_dir)}")
        print(f"🔗 Open index.html to view the result.")
    except Exception as e:
        import traceback
        print("\n❌ Generation Failed during pipeline execution.")
        traceback.print_exc()
        print(f"Error Message: {e}")

if __name__ == "__main__":
    asyncio.run(main())
