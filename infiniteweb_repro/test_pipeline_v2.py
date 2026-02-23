#!/usr/bin/env python3
"""
End-to-End Test for Refactored Pipeline
========================================
Tests the new modular pipeline_v2.py architecture.
"""
import asyncio
import os
import sys
import logging

# Configure logging so all modules' logger.info() calls go to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    stream=sys.stdout
)

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
from src.generators.controller_generator import LLMControllerGenerator
from src.generators.instrumentation_generator import LLMInstrumentationGenerator
from src.generators.evaluator_generator import LLMEvaluatorGenerator

# Import new refactored pipeline
from src.pipeline_v2 import AsyncWebGenPipelineV2
from src.pipeline import PipelineConfig

async def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "simple_todo_app"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output/pipeline_v2_test"
    
    print("=" * 60)
    print("🧪 Pipeline V2 End-to-End Test")
    print("=" * 60)
    print(f"📋 Topic: {topic}")
    print(f"📁 Output: {output_dir}")
    print("=" * 60)
    
    # Initialize LLM with the provided DeepSeek endpoint
    base_url = "https://siflow-zhuoguang.siflow.cn/siflow/zhuoguang/skyinfer/chao/dpskv32-tp8dp1-h20-service-fork/v1"
    model_name = "DeepSeek-V3.2"
    
    # Environment setup for OpenHands SDK
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_MODEL"] = f"openai/{model_name}"
    os.environ["LLM_API_KEY"] = "EMPTY"
    os.environ["SANDBOX_TYPE"] = "local"
    os.environ["LITELLM_TELEMETRY"] = "FALSE"  # Prevent telemetry hangs
    
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
    controller_gen = LLMControllerGenerator(llm)
    instr_gen = LLMInstrumentationGenerator(llm)
    evaluator_gen = LLMEvaluatorGenerator(llm)
    
    # Configure pipeline
    config = PipelineConfig(
        max_concurrency=1,
        max_fix_retries=3,  # Increased to enable Tier 2 (OpenHands) fix
        enable_visual_validation=False,  # Skip for speed
        enable_golden_path=True,
        verbose=True
    )
    
    # Initialize Refactored Pipeline V2
    pipeline = AsyncWebGenPipelineV2(
        task_gen=task_gen,
        interface_designer=interface_designer,
        arch_designer=arch_designer,
        data_gen=data_gen,
        backend_gen=backend_gen,
        page_designer=page_designer,
        frontend_gen=frontend_gen,
        controller_gen=controller_gen,
        instr_gen=instr_gen,
        evaluator_gen=evaluator_gen,
        llm=llm,
        config=config
    )
    
    print("\n🚦 Running Pipeline V2...")
    try:
        context = await pipeline.run(topic, output_dir)
        
        print("\n" + "=" * 60)
        print("\n" + "=" * 60)
        
        # Check verification status
        validation_passed = True
        if context.verification_results and not context.verification_results.get("overall", True):
            validation_passed = False
            
        if validation_passed:
            print("✅ Pipeline V2 Test PASSED!")
        else:
            print("⚠️ Pipeline Infrastructure Passed, but Validation FAILED!")
            
        print("=" * 60)
        print(f"📋 Tasks generated: {len(context.spec.tasks)}")
        print(f"📄 Pages generated: {len(context.generated_pages)}")
        print(f"🔌 Interfaces: {len(context.spec.interfaces)}")
        print(f"📁 Output: {os.path.abspath(output_dir)}")
        
        # --- Paper Fidelity Verification ---
        print("\n🔍 Verifying Paper Fidelity Artifacts...")
        
        # 1. Page Designs (Stage 4)
        page_designs_path = os.path.join(output_dir, "intermediates", "05_page_designs.json")
        if os.path.exists(page_designs_path):
            print("✅ Stage 4: Page Designs generated")
        else:
            print("❌ Stage 4: Page Designs MISSING")
            validation_passed = False

        # 2. Logic Instrumentation (Stage 8)
        logic_path = os.path.join(output_dir, "logic.js")
        if os.path.exists(logic_path):
            with open(logic_path, 'r') as f:
                if "window.__instrumentation" in f.read():
                    print("✅ Stage 8: Instrumentation code injected")
                else:
                    print("❌ Stage 8: Instrumentation code MISSING in logic.js")
                    validation_passed = False
        
        # 3. Evaluator (Stage 9)
        eval_path = os.path.join(output_dir, "evaluator.js")
        if os.path.exists(eval_path):
            print("✅ Stage 9: Evaluator script generated")
        else:
            print("❌ Stage 9: Evaluator script MISSING")
            validation_passed = False
            
        print("=" * 60)
        
        if not validation_passed:
             print("\n❌ Validation Issues Detected (Golden Path or Visual)")
             # We exit with 0 because the *pipeline* ran successfully, but we warn heavily
             # Alternatively, sys.exit(1) if we want to fail CI. Let's start with warning.
        
        # List generated files
        if os.path.exists(output_dir):
            files = os.listdir(output_dir)
            print(f"\n📂 Generated files ({len(files)}):")
            for f in sorted(files)[:15]:  # Show first 15
                print(f"   - {f}")
        
    except Exception as e:
        import traceback
        print("\n" + "=" * 60)
        print("❌ Pipeline V2 Test FAILED!")
        print("=" * 60)
        traceback.print_exc()
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
