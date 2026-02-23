import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

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
    output_dir = "output/mature_agents_v12_production"
    
    print(f"🚀 Starting v12 Regeneration with Integration Testing for: {topic}")
    print(f"📂 Target: {output_dir}")
    
    # Initialize LLMs for different machines
    # 使用 siflow API 生成前后端代码 (Generation)
    gen_llm = CustomLLMProvider(
        base_url="https://siflow-zhuoguang.siflow.cn/siflow/zhuoguang/skyinfer/chao/dpskv32-tp8dp1-h20-service-fork/v1",
        model="DeepSeek-V3.2" # 假设模型名称，如果不对请告诉我
    )
    
    # 10.166.97.108: 用于规划、修复、Agent等其他流程 (Planning & Verification)
    plan_llm = CustomLLMProvider(base_url="http://10.166.97.108:8000/v1")
    
    # Initialize Generators
    task_gen = LLMTaskGenerator(plan_llm)
    interface_designer = LLMInterfaceDesigner(plan_llm)
    arch_designer = LLMArchitectDesigner(plan_llm)
    data_gen = LLMDataGenerator(plan_llm)
    
    # 前后端代码生成使用 gen_llm
    backend_gen = LLMBackendGenerator(gen_llm)
    page_designer = LLMPageDesigner(plan_llm)
    frontend_gen = LLMFrontendGenerator(gen_llm)
    
    instr_gen = LLMInstrumentationGenerator(plan_llm)
    evaluator_gen = LLMEvaluatorGenerator(plan_llm)
    
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
        evaluator_gen,
        llm=plan_llm  # Agent 和修复流程使用 plan_llm
    )
    
    try:
        await pipeline.run(topic, output_dir)
        print("\n✨ v12 Regeneration Completed Successfully!")
    except Exception as e:
        print(f"\n❌ Pipeline Failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
