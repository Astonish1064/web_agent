import argparse
import sys
import os

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pipeline.web_gen_pipeline import WebGenPipeline
from src.llm import CustomLLMProvider

# Generators
from src.generators.task_generator import LLMTaskGenerator
from src.generators.interface_designer import LLMInterfaceDesigner
from src.generators.architecture_designer import LLMArchitectDesigner
from src.generators.data_generator import LLMDataGenerator
from src.generators.backend_generator import LLMBackendGenerator
from src.generators.page_designer import LLMPageDesigner
from src.generators.frontend_generator import LLMFrontendGenerator
from src.generators.instrumentation_generator import LLMInstrumentationGenerator
from src.generators.evaluator_generator import LLMEvaluatorGenerator

def main():
    parser = argparse.ArgumentParser(description="InfiniteWeb Framework Reproduction (Full 17-Prompt Flow)")
    parser.add_argument("--seed", type=str, default="online_bookstore", help="Website seed")
    parser.add_argument("--output", type=str, default="output", help="Directory to save generated files")
    parser.add_argument("--vllm-url", type=str, default=None, help="Single vLLM URL (fallback when --gen-url/--plan-url not set)")
    parser.add_argument("--gen-url", type=str, default=None, help="vLLM URL for frontend/backend code generation")
    parser.add_argument("--plan-url", type=str, default=None, help="vLLM URL for planning, fixing, and other tasks")
    
    args = parser.parse_args()

    # Resolve endpoints
    default_url = args.vllm_url or "http://10.166.69.135:8000/v1"
    gen_url = args.gen_url or default_url
    plan_url = args.plan_url or default_url
    
    print(f"🚀 Initializing InfiniteWeb Generator for '{args.seed}'...")
    print(f"🔌 Generation LLM:  {gen_url}")
    print(f"🔌 Planning LLM:    {plan_url}")
    
    # Initialize LLM providers
    try:
        gen_llm = CustomLLMProvider(base_url=gen_url)
        if gen_url == plan_url:
            plan_llm = gen_llm  # reuse same client if same endpoint
        else:
            plan_llm = CustomLLMProvider(base_url=plan_url)
    except Exception as e:
        print(f"Error connecting to LLM: {e}")
        return

    # Initialize Generators
    # gen_llm  → frontend/backend code generation (e.g. Qwen32B on 172.16.152.159)
    # plan_llm → planning, fixing, and everything else (e.g. DeepSeek-V3.1 on 10.166.97.108)
    print("🛠  Initializing Generators...")
    task_gen = LLMTaskGenerator(plan_llm)
    interface_designer = LLMInterfaceDesigner(plan_llm)
    arch_designer = LLMArchitectDesigner(plan_llm)
    data_gen = LLMDataGenerator(plan_llm)
    backend_gen = LLMBackendGenerator(gen_llm)
    page_designer = LLMPageDesigner(plan_llm)
    frontend_gen = LLMFrontendGenerator(gen_llm)
    instr_gen = LLMInstrumentationGenerator(plan_llm)
    evaluator_gen = LLMEvaluatorGenerator(plan_llm)
    
    # Setup Pipeline
    pipeline = WebGenPipeline(
        task_gen=task_gen,
        interface_designer=interface_designer,
        arch_designer=arch_designer,
        data_gen=data_gen,
        backend_gen=backend_gen,
        page_designer=page_designer,
        frontend_gen=frontend_gen,
        instr_gen=instr_gen,
        evaluator_gen=evaluator_gen
    )

    full_output_path = os.path.join(args.output, args.seed)
    print(f"▶️  Starting Pipeline Execution...")
    
    try:
        context = pipeline.run(args.seed, full_output_path)
        print("\n✅ Generation Complete!")
        print(f"📂 Files saved to: {full_output_path}")
        print(f"🌐 Open {os.path.join(full_output_path, 'index.html')} to view.")
    except Exception as e:
        print(f"\n❌ Pipeline Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
