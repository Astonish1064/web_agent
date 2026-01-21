import argparse
import sys
import os

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import WebGenPipeline
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
    parser.add_argument("--vllm-url", type=str, default="http://10.166.69.135:8000/v1", help="vLLM API Base URL")
    
    args = parser.parse_args()
    
    print(f"🚀 Initializing InfiniteWeb Generator for '{args.seed}'...")
    print(f"🔌 Connecting to LLM at {args.vllm_url}...")
    
    # Initialize LLM
    try:
        llm = CustomLLMProvider(base_url=args.vllm_url)
    except Exception as e:
        print(f"Error connecting to LLM: {e}")
        return

    # Initialize Generators
    print("🛠  Initializing Generators...")
    task_gen = LLMTaskGenerator(llm)
    interface_designer = LLMInterfaceDesigner(llm)
    arch_designer = LLMArchitectDesigner(llm)
    data_gen = LLMDataGenerator(llm)
    backend_gen = LLMBackendGenerator(llm)
    page_designer = LLMPageDesigner(llm)
    frontend_gen = LLMFrontendGenerator(llm)
    instr_gen = LLMInstrumentationGenerator(llm)
    evaluator_gen = LLMEvaluatorGenerator(llm)
    
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
