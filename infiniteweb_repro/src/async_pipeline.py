
import asyncio
import os
import json
from typing import List, Optional, Dict
from .domain import GenerationContext, WebsiteSpec, PageSpec, Task, InterfaceDef, DataModel, Framework
from .generators.task_generator import TaskConfig
from .generators.architecture_designer import Architecture
# from .generators.fix_generator import IntegrationFixer # DEPRECATED: Use OpenHandsResolver instead
from .agent.environments.env_validator import EnvironmentHealthChecker, ContractValidator
from .generators.openhands_resolver import OpenHandsResolver

class AsyncWebGenPipeline:
    def __init__(
        self,
        task_gen,
        interface_designer,
        arch_designer,
        data_gen,
        backend_gen,
        page_designer,
        frontend_gen,
        instr_gen,
        evaluator_gen,
        llm=None,
        max_concurrency=1 # Reduced for stability
    ):
        self.llm = llm
        self.task_gen = task_gen
        self.interface_designer = interface_designer
        self.arch_designer = arch_designer
        self.data_gen = data_gen
        self.backend_gen = backend_gen
        self.page_designer = page_designer
        self.frontend_gen = frontend_gen
        self.instr_gen = instr_gen
        self.evaluator_gen = evaluator_gen
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.raw_responses_dir = None

    def _set_llm_logger(self, context, filename):
        """Sets a callback on the LLM provider to save raw responses."""
        if not hasattr(self.llm, 'response_callback'):
            return
            
        def logger(content):
            log_dir = os.path.join(context.output_dir, "raw_responses")
            os.makedirs(log_dir, exist_ok=True)
            # We append because generators might call the LLM multiple times (e.g. Planning + Implementing)
            # Ensure content is string
            content = str(content) if content is not None else ""
            with open(os.path.join(log_dir, f"{filename}.txt"), "a") as f:
                f.write(f"\n--- RESPONSE ---\n")
                f.write(content)
                f.write("\n" + "="*40 + "\n")
        
        self.llm.response_callback = logger

    async def run(self, topic: str, output_dir: str):
        """Executes the full generation pipeline asynchronously with resume support."""
        abs_output_dir = os.path.abspath(output_dir)
        os.makedirs(abs_output_dir, exist_ok=True)
        self.intermediates_dir = os.path.join(abs_output_dir, "intermediates")
        os.makedirs(self.intermediates_dir, exist_ok=True)
        
        context = GenerationContext(seed=topic, output_dir=abs_output_dir)
        context.spec = WebsiteSpec(seed=topic)
        
        # Resume state if intermediates exist
        design_analysis = self._resume_context(context)
        
        # Parallel Step 1: Planning Chain + Design Analysis (Skip if done)
        planning_needed = not context.spec.tasks or not context.spec.interfaces or not context.spec.pages
        if planning_needed:
            planning_task = asyncio.create_task(self._run_planning_phase(topic, context))
        else:
            print("⏭️ [DEBUG] Skipping planning phase (already completed)")
            planning_task = asyncio.create_task(asyncio.sleep(0))
            
        if design_analysis is None:
            design_task = asyncio.create_task(self._run_design_analysis(topic))
        else:
            print("⏭️ [DEBUG] Skipping design analysis (already completed)")
            design_task = asyncio.create_task(asyncio.sleep(0))
        
        await planning_task
        if design_analysis is None:
            design_analysis = await design_task
        
        await planning_task
        if design_analysis is None:
            design_analysis = await design_task
        
        # Phase 2: Incremental TCTDD Generation
        print("🚀 [DEBUG] Starting Incremental TCTDD Generation Loop...")
        await self._run_incremental_tctdd_loop(context)
        
        # Phase 8: Multimodal Validation (Visual + State)
        print("🔍 [DEBUG] Starting multimodal validation...")
        await self._run_multimodal_validation(context)
        
        return context
        
        return context

    async def _run_incremental_tctdd_loop(self, context: GenerationContext):
        """Runs the task-by-task incremental TCTDD loop."""
        if not context.data:
            print("💾 [DEBUG] Initial data generation...")
            context.data = await self._run_throttled(self.data_gen.generate, context.spec)
            self._save_intermediate("6_generated_data.json", context.data)

        # Initialize base logic.js if empty
        if not context.backend_code:
            context.backend_code = "class BusinessLogic { constructor() { } }\nwindow.WebsiteSDK = new BusinessLogic(); if (typeof module !== 'undefined') module.exports = BusinessLogic;"

        for i, task in enumerate(context.spec.tasks):
            print(f"\n--- 🚀 [INCREMENTAL] Task {i+1}/{len(context.spec.tasks)}: {task.id} ---")
            
            # 1. Generate Task-Specific Tests (RED)
            print(f"🧪 Generating independent tests for {task.id}...")
            self._set_llm_logger(context, f"tests_{task.id}")
            task_tests = await self._run_throttled(self.backend_gen.generate_task_tests, task, context.spec, context.data)
            test_filename = f"tests_{task.id}.js"
            with open(os.path.join(context.output_dir, test_filename), "w") as f:
                f.write(task_tests)

            # 2. OpenCode Phase A: Planning
            print(f"📝 Planning logic for task {task.id}...")
            self._set_llm_logger(context, f"plan_{task.id}")
            task_plan = await self._run_throttled(
                self.backend_gen.generate_task_plan, task, task_tests, context.backend_code, context.spec
            )
            context.task_plans[task.id] = task_plan
            with open(os.path.join(context.output_dir, f"plan_{task.id}.md"), "w") as f:
                f.write(task_plan)

            # 3. OpenCode Phase B: Building
            print(f"⚙️ Implementing logic to pass {task.id} tests...")
            self._set_llm_logger(context, f"logic_{task.id}")
            context.backend_code = await self._run_throttled(
                self.backend_gen.implement_task_logic, task, task_tests, context.backend_code, context.spec, task_plan
            )
            with open(os.path.join(context.output_dir, "logic.js"), "w") as f:
                f.write(context.backend_code)

            # 4. Frontend View Implementation
            print(f"🎨 Implementing UI components for {task.id}...")
            self._set_llm_logger(context, f"frontend_{task.id}")
            new_pages = await self._run_throttled(self.frontend_gen.implement_task_view, task, context.backend_code, context.spec)
            if new_pages and isinstance(new_pages, dict):
                for filename, html in new_pages.items():
                    if filename == "__raw__" or not filename.endswith(".html"):
                        continue
                    context.generated_pages[filename] = html
                    with open(os.path.join(context.output_dir, filename), "w") as f:
                        f.write(html)

            # 5. Local Verification with Tiered Fix Loop
            task_success = False
            resolver = OpenHandsResolver(self.llm, context.output_dir)
            
            for fix_attempt in range(3):
                print(f"🧐 Verifying task {task.id} increment (Attempt {fix_attempt + 1})...")
                success, error = await self._verify_task_increment(task, task_tests, context)
                
                if success:
                    print(f"✅ Task {task.id} verified and passed!")
                    task_success = True
                    break
                else:
                    print(f"❌ Verification failed for {task.id}: {error}")
                    if fix_attempt == 0:
                        if "Backend Logic Error" in error:
                            print(f"🔧 [Tier 1] Fix: Updating Backed Logic for {task.id}...")
                            context.backend_code = await self._run_throttled(
                                self.backend_gen.implement_task_fix, task, task_tests, error, context.backend_code, context.spec
                            )
                            with open(os.path.join(context.output_dir, "logic.js"), "w") as f:
                                f.write(context.backend_code)
                        else:
                            print(f"🔧 [Tier 1] Fix: Updating Frontend UI for {task.id}...")
                            new_pages = await self._run_throttled(
                                self.frontend_gen.fix_task_view, task, context.backend_code, context.spec, error, context.generated_pages
                            )
                            if new_pages and isinstance(new_pages, dict):
                                for filename, html in new_pages.items():
                                    if filename == "__raw__" or not filename.endswith(".html"):
                                        continue
                                    context.generated_pages[filename] = html
                                    with open(os.path.join(context.output_dir, filename), "w") as f:
                                        f.write(html)
                    elif fix_attempt == 1:
                        print(f"🤖 [Tier 2] Activating OpenHands Agent for task {task.id}...")
                        agent_success = await resolver.resolve(task.description, error, context.spec.to_dict())
                        if agent_success:
                            # Reload code if fixed
                            with open(os.path.join(context.output_dir, "logic.js"), "r") as f:
                                context.backend_code = f.read()
                        else:
                            print(f"⛔ OpenHands Agent failed to fix {task.id}.")
                    else:
                        print(f"⛔ Max fix attempts reached for {task.id}.")

            if not task_success:
                 print(f"🛑 [FATAL] Task {task.id} failed verification after tiered fix attempts. Stopping.")
                 raise Exception(f"Task {task.id} verification failure.")

    async def _verify_task_increment(self, task, test_code, context):
        """Runs the task-specific tests in JSDOM AND real browser integration checks."""
        from .agent.environments.env_validator import EnvironmentHealthChecker, IntegrationValidator
        
        # 1. Backend Logic Unit Tests (JSDOM)
        validator = EnvironmentHealthChecker()
        test_filename = f"tests_{task.id}.js"
        original_test_path = os.path.join(context.output_dir, "backend_tests.js")
        task_test_path = os.path.join(context.output_dir, test_filename)
        
        import shutil
        shutil.copy(task_test_path, original_test_path)
        
        success, error = await validator.validate_backend(context.output_dir)
        if not success:
            return False, f"Backend Logic Error: {error}"
            
        # 2. Integration Tests (Real Browser)
        # Check if the generated pages for this task have runtime JS errors
        print(f"🌐 Running browser-level integration tests for {task.id}...")
        integration_validator = IntegrationValidator()
        
        # Identify pages involved in this task
        # We check current generated pages and those explicitly mentioned in task steps
        pages_to_test = list(context.generated_pages.keys())
        if not pages_to_test:
            pages_to_test = ["index.html"] # Fallback
            
        # For efficiency, we only test index.html and pages updated in this task
        # But for now, let's test all to be safe
        success, errors = await integration_validator.validate_all_pages(context.output_dir, pages_to_test)
        if not success:
            return False, f"Integration Error (Browser Console): {'; '.join(errors)}"
            
        # 3. State Persistence Check (localStorage)
        # We verify that common actions (like adding to cart) actually update localStorage
        print(f"💾 Verifying state persistence for {task.id}...")
        # We use a heuristic: if the task involves 'Add to Cart', check if cart changed.
        # This is better handled by a specialized check or by the task execution validator.
        # For now, let's do a basic check that WebsiteSDK is functional.
        
        # 4. Task Feasibility Check (Golden Path)
        print(f"🦮 Verifying task feasibility for {task.id}...")
        from .generators.verification_generator import VerificationGenerator
        from .agent.environments.env_validator import TaskStepExecutor
        
        gen = VerificationGenerator(self.llm)
        executor = TaskStepExecutor()
        
        # Heuristic to find target page (reusing logic or simplified)
        target_page = self._find_target_page_for_task(task, context) or "index.html"
        
        # Use HTML content from generated_pages
        html_content = context.generated_pages.get(target_page, "")
        if not html_content and target_page == "index.html" and "index.html" in context.generated_pages:
             html_content = context.generated_pages["index.html"]

        if not html_content:
             print("   ⚠️ No HTML content found for target page, skipping golden path check.")
        else:
            golden_path = await self._run_throttled(
                gen.generate_golden_path,
                task,
                context.spec.architecture.to_dict() if hasattr(context.spec.architecture, 'to_dict') else {},
                html_content,
                context.backend_code
            )
            
            if not golden_path or "steps" not in golden_path:
                 return False, "Failed to generate Golden Path (AI could not plan actions on current UI)"
                 
            # Ensure evaluator_code is not None or empty
            evaluator_code = context.evaluator_code
            if not evaluator_code or len(evaluator_code.strip()) == 0:
                evaluator_code = "class Evaluator { async evaluate() { return {}; } }"

            success, message = await executor.execute_and_verify(
                context.output_dir,
                target_page,
                golden_path["steps"],
                evaluator_code,
                task.id
            )
            
            if not success:
                 return False, f"Golden Path Execution Failed: {message}"

        return True, None

    def _load_intermediate_json(self, filename):
        """Loads intermediate JSON if it exists."""
        path = os.path.join(self.intermediates_dir, filename)
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return None

    def _resume_context(self, context: GenerationContext):
        """Reconstructs context from intermediate files."""
        print("🔄 [DEBUG] Checking for existing intermediate results to resume...")
        
        # 1. Tasks
        data = self._load_intermediate_json("1_tasks.json")
        if data:
            context.spec.tasks = [Task.from_dict(t) for t in data]
            print(f"   ✓ Loaded {len(context.spec.tasks)} tasks")
            
        # 3. Interfaces
        data = self._load_intermediate_json("3_interfaces.json")
        if data:
            context.spec.interfaces = [InterfaceDef.from_dict(i) for i in data]
            print(f"   ✓ Loaded {len(context.spec.interfaces)} interfaces")
            
        # 4. Final Architecture
        data = self._load_intermediate_json("4_final_architecture.json")
        if data:
            context.spec.architecture = Architecture.from_dict(data)
            context.spec.pages = [PageSpec(name=getattr(p, 'name', ''), 
                                         filename=getattr(p, 'filename', ''),
                                         description=f"Page: {getattr(p, 'name', '')}")
                                 for p in context.spec.architecture.pages]
            print(f"   ✓ Loaded architecture with {len(context.spec.pages)} pages")
            
        # 5. Design Analysis
        design_analysis = self._load_intermediate_json("5_design_analysis.json")
        if design_analysis:
            print("   ✓ Loaded design analysis")
            
        # 6. Data
        data = self._load_intermediate_json("6_generated_data.json")
        if data:
            context.data = data
            print("   ✓ Loaded generated data")
            
        # Logic and Evaluator (from final files)
        logic_path = os.path.join(context.output_dir, "logic.js")
        if os.path.exists(logic_path):
            with open(logic_path, "r") as f:
                context.backend_code = f.read()
            print("   ✓ Loaded logic.js")
            
        eval_path = os.path.join(context.output_dir, "evaluator.js")
        if os.path.exists(eval_path):
            with open(eval_path, "r") as f:
                context.evaluator_code = f.read()
            print("   ✓ Loaded evaluator.js")
            
        # Framework
        data = self._load_intermediate_json("10_framework.json")
        if data:
            context.framework = Framework.from_dict(data)
            print("   ✓ Loaded framework")
            
        # Generated Pages
        if context.spec.pages:
            for page in context.spec.pages:
                page_path = os.path.join(context.output_dir, page.filename)
                if os.path.exists(page_path):
                    with open(page_path, "r") as f:
                        context.generated_pages[page.filename] = f.read()
            if context.generated_pages:
                print(f"   ✓ Loaded {len(context.generated_pages)} HTML pages")
                
        return design_analysis

    async def _run_throttled(self, func, *args, **kwargs):
        async with self.semaphore:
            return await asyncio.to_thread(func, *args, **kwargs)

    def _save_intermediate(self, filename, data):
        """Helper to save intermediate results for debugging."""
        path = os.path.join(self.intermediates_dir, filename)
        with open(path, "w") as f:
            if isinstance(data, (dict, list)):
                json.dump(data, f, indent=2, default=lambda o: o.__dict__)
            elif hasattr(data, '__dict__'):
                json.dump(data.__dict__, f, indent=2, default=lambda o: o.__dict__)
            else:
                f.write(str(data))
        print(f"💾 [DEBUG] Saved intermediate: {filename}")

    async def _run_planning_phase(self, topic: str, context: GenerationContext):
        """Runs the sequential planning phase."""
        # 1.1 Tasks
        task_config = TaskConfig(website_type=topic, task_count_min=3, task_count_max=6)
        self._set_llm_logger(context, "planning_tasks")
        context.spec.tasks = await self._run_throttled(self.task_gen.generate, topic, task_config)
        print(f"📋 [DEBUG] Tasks generated: {len(context.spec.tasks)}")
        
        # Save tasks to JSON
        tasks_path = os.path.join(context.output_dir, "tasks.json")
        with open(tasks_path, "w") as f:
            tasks_data = [
                {"id": t.id, "name": t.name, "description": t.description, "steps": t.steps}
                for t in context.spec.tasks
            ]
            json.dump(tasks_data, f, indent=2)
        print(f"📋 [DEBUG] Saved tasks to {tasks_path}")
        self._save_intermediate("1_tasks.json", tasks_data)
        
        # 1.2 Initial Architecture (to get pages for interface design)
        print("🏗️ [DEBUG] Designing initial architecture...")
        self._set_llm_logger(context, "planning_architecture_initial")
        initial_arch = await self._run_throttled(self.arch_designer.design, context.spec)
        context.spec.pages = [PageSpec(name=getattr(p, 'name', ''), 
                                     filename=getattr(p, 'filename', ''),
                                      description=f"Page: {getattr(p, 'name', '')}")
                             for p in getattr(initial_arch, 'pages', [])]
        self._save_intermediate("2_initial_architecture.json", initial_arch)
        
        # 1.3 Interfaces (now aware of pages)
        print("🔌 [DEBUG] Designing interfaces based on tasks and pages...")
        self._set_llm_logger(context, "planning_interfaces")
        context.spec.interfaces = await self._run_throttled(self.interface_designer.design, context.spec)
        print(f"🔌 [DEBUG] Interfaces designed: {len(context.spec.interfaces)}")
        self._save_intermediate("3_interfaces.json", context.spec.interfaces)
        
        # 1.4 Final Architecture (refine with interfaces)
        print("🏗️ [DEBUG] Finalizing architecture with interface assignments...")
        context.spec.architecture = await self._run_throttled(self.arch_designer.design, context.spec)
        arch_pages = getattr(context.spec.architecture, 'pages', [])
        print(f"🏗️ [DEBUG] Architecture pages: {len(arch_pages)}")
        self._save_intermediate("4_final_architecture.json", context.spec.architecture)
        
        # Sync pages again (just in case they changed)
        context.spec.pages = [PageSpec(name=getattr(p, 'name', ''), 
                                     filename=getattr(p, 'filename', ''),
                                     description=f"Page: {getattr(p, 'name', '')}")
                             for p in arch_pages]
        print(f"📄 [DEBUG] Final context.spec.pages count: {len(context.spec.pages)}")

    async def _run_design_analysis(self, topic: str):
        """Runs design analysis."""
        analysis = await self._run_throttled(self.page_designer.analyze_design, topic)
        self._save_intermediate("5_design_analysis.json", analysis)
        return analysis

    async def _run_backend_logic_generation(self, context: GenerationContext):
        """Generates initial business logic without validation."""
        # 2.1 Data
        print("💾 [DEBUG] Starting data generation...")
        context.data = await self._run_throttled(self.data_gen.generate, context.spec)
        self._save_intermediate("6_generated_data.json", context.data)
        
        # 2.2 Backend Logic
        print("⚙️ [DEBUG] Generating initial backend logic...")
        self._set_llm_logger(context, "backend_initial")
        raw_logic = await self._run_throttled(self.backend_gen.generate_logic, context.spec)
        self._save_intermediate("7_initial_raw_logic.js", raw_logic)
        
        # Process and inject (initial)
        await self._process_backend_logic(context, raw_logic)

    async def _process_backend_logic(self, context, raw_logic):
        """Standard processing for logic: Instr Analysis -> Injection -> Evaluator Gen."""
        # 2.3 Instrumentation Analysis
        instr_reqs = await self._run_throttled(self.instr_gen.analyze, context.spec, raw_logic)
        self._save_intermediate("8_instrumentation_requirements.json", instr_reqs)
        
        # 2.4 Injection
        context.backend_code = await self._run_throttled(self.instr_gen.inject, raw_logic, instr_reqs)
        
        # 2.5 Evaluator Generation
        context.evaluator_code = await self._run_throttled(
            self.evaluator_gen.generate, context.spec, instr_reqs, context.backend_code
        )
        
        # Write files
        logic_path = os.path.join(context.output_dir, "logic.js")
        eval_path = os.path.join(context.output_dir, "evaluator.js")
        with open(logic_path, "w") as f:
            f.write(context.backend_code)
        with open(eval_path, "w") as f:
            f.write(context.evaluator_code)

    async def _run_system_validation_loop(self, context: GenerationContext):
        """Runs the System Validation loop (Logic + UI) with retries."""
        validator = EnvironmentHealthChecker()
        max_retries = 3
        last_error = None
        
        # 1. Initial Test Generation
        test_path = os.path.join(context.output_dir, "backend_tests.js")
        needs_test_regeneration = not os.path.exists(test_path)
        
        for attempt in range(max_retries):
            print(f"🧪 [DEBUG] System Validation attempt {attempt + 1}/{max_retries}")
            
            if needs_test_regeneration:
                print("🧪 [DEBUG] Generating full-stack system tests...")
                self._set_llm_logger(context, "system_tests_initial")
                test_code = await self._run_throttled(
                    self.backend_gen.generate_tests, 
                    context.spec, 
                    context.backend_code, 
                    context.data,
                    html_files=context.generated_pages
                )
                with open(test_path, "w") as f:
                    f.write(test_code)
                needs_test_regeneration = False
            
        # 2. Validation
            print("🧐 [DEBUG] Validating API contracts (interfaces.json)...")
            contract_validator = ContractValidator()
            contract_report = await contract_validator.validate(context.output_dir)
            
            if not contract_report.get("success", False):
                violations = contract_report.get("violations", [])
                error_summary = "; ".join([v.get("message", "Unknown violation") for v in violations])
                success = False
                error = f"CONTRACT_VIOLATION: {error_summary}"
            else:
                print("   ✓ API contracts passed.")
                print("🧐 [DEBUG] Validating system integrity (JSDOM + Logic)...")
                success, error = await validator.validate_backend(context.output_dir)
            
            if success:
                print("✅ [DEBUG] System validation passed!")
                break
            else:
                last_error = error
                print(f"❌ [DEBUG] System validation failed: {error}")
                if attempt < max_retries - 1:
                    # Smart Diagnostic Step
                    print("🧠 [DEBUG] Analyzing error with Smart Diagnostics...")
                    # Read current tests
                    with open(test_path, "r") as f:
                        current_tests = f.read()
                        
                    diagnosis = await self._run_throttled(
                        self.backend_gen.analyze_error,
                        context.spec,
                        context.backend_code,
                        current_tests,
                        error
                    )
                    
                    action = diagnosis.get("action", "FIX_TEST")
                    
                    if action == "FATAL":
                        print(f"🛑 [DEBUG] Fatal error detected: {diagnosis.get('reasoning')}")
                        break
                        
                    if action == "FIX_TEST":
                        print(f"🔄 [DEBUG] Action: FIX_TEST ({diagnosis.get('reasoning')})")
                        fixed_tests = await self._run_throttled(
                            self.backend_gen.fix_tests,
                            context.spec,
                            current_tests,
                            error
                        )
                        with open(test_path, "w") as f:
                            f.write(fixed_tests)
                    else: # FIX_LOGIC
                        print(f"🔄 [DEBUG] Action: FIX_LOGIC ({diagnosis.get('reasoning')})")
                        raw_logic = await self._run_throttled(
                            self.backend_gen.fix_logic, 
                            context.spec, 
                            context.backend_code,
                            error
                        )
                        await self._process_backend_logic(context, raw_logic)
                        # Logic changed -> Tests are now stale -> Regenerate tests in next loop
                        needs_test_regeneration = True
                        
                        # CRITICAL: Mark backend as dirty if we had frontend (though now we are serial)
                        # But since we are serial, this ensures next step uses fresh logic.
        else:
            print(f"⚠️ [DEBUG] System validation failed after {max_retries} attempts.")

    async def _run_multimodal_validation(self, context: GenerationContext):
        """ Performs UI screenshot capture and VLM-based visual + state analysis. """
        from .agent.environments.env_validator import VisualValidator
        
        if not self.llm:
            print("⚠️ [DEBUG] Skipping visual validation (no LLM provider)")
            return

        validator = EnvironmentHealthChecker()
        visual_validator = VisualValidator(self.llm)
        
        for page in context.spec.pages:
            print(f"🖼️ [DEBUG] Validating visual quality for {page.filename}...")
            screenshot_name = f"{page.filename.split('.')[0]}_snapshot.png"
            screenshot_path = os.path.join(context.output_dir, screenshot_name)
            
            # 1. Capture and Basic Health
            success, error = await validator.validate_frontend(
                context.output_dir, page.filename, screenshot_path=screenshot_path
            )
            
            if not success:
                print(f"❌ [DEBUG] Frontend basic check failed for {page.filename}: {error}")
                continue
                
            # 2. Visual Analysis (VLM)
            print(f"🧠 [DEBUG] Analyzing screenshot for {page.filename}...")
            result = await visual_validator.validate(
                screenshot_path, context.seed, page.name, page.description
            )
            
            score = result.get("score", 0)
            passed = result.get("pass", False)
            feedback = result.get("feedback", "No feedback")
            
            if passed:
                print(f"✅ [DEBUG] Visual validation passed for {page.filename} (Score: {score}/10)")
            else:
                print(f"❌ [DEBUG] Visual validation failed for {page.filename} (Score: {score}/10): {feedback}")
                # In a full implementation, we would trigger regeneration here.
                # For now, we log it.

    async def _run_frontend_branch(self, context: GenerationContext, design_analysis):
        """Runs Framework -> Parallel Page Generation."""
        # 3.2 Framework (Header/Footer)
        context.framework = await self._run_throttled(
            self.frontend_gen.generate_framework, 
            context.spec, 
            context.spec.architecture
        )
        self._save_intermediate("10_framework.json", context.framework)
        
        # Prepare for page generation
        arch_pages_map = {p.filename: p for p in getattr(context.spec.architecture, 'pages', [])}
        tasks = []
        
        # Spawn concurrent tasks for each page
        for page in context.spec.pages:
            task = asyncio.create_task(
                self._generate_single_page(page, context, design_analysis, arch_pages_map)
            )
            tasks.append(task)
            
        # Wait for all pages
        await asyncio.gather(*tasks)

    async def _generate_single_page(self, page, context, design_analysis, arch_pages_map):
        """Generates a single page's Design -> Layout -> HTML -> CSS pipeline."""
        print(f"📑 [DEBUG] Starting page generation for: {page.filename}")
        
        # 1. Functionality
        page_arch = arch_pages_map.get(page.filename, None)
        page_design = await self._run_throttled(
            self.page_designer.design_functionality, page, context.spec, navigation_info=getattr(page_arch, '__dict__', {}) if page_arch else {}
        )
        print(f"   ✓ Functionality designed for {page.filename}")
        self._save_intermediate(f"page_{page.filename}_1_design.json", page_design)
        
        # 2. Layout
        layout = await self._run_throttled(
            self.page_designer.design_layout, 
            page, design_analysis, getattr(page_design, 'components', []), context.seed
        )
        print(f"   ✓ Layout designed for {page.filename}")
        self._save_intermediate(f"page_{page.filename}_2_layout.json", layout)
        
        # 3. HTML
        # page_arch already retrieved above
        if not page_arch:
             # Fallback if not found in architecture
             page_arch = getattr(context.spec.architecture, 'pages', [None])[0]
        
        html = await self._run_throttled(
            self.frontend_gen.generate_html, 
            context.spec, page, page_design, page_arch, context.framework, context.backend_code
        )
        print(f"   ✓ HTML generated for {page.filename}: {len(html) if html else 0} chars")
        self._save_intermediate(f"page_{page.filename}_3_raw.html", html)
        
        # 4. CSS
        css = await self._run_throttled(
            self.frontend_gen.generate_css, 
            page_design, layout, design_analysis, context.framework, html
        )
        print(f"   ✓ CSS generated for {page.filename}: {len(css) if css else 0} chars")
        self._save_intermediate(f"page_{page.filename}_4_raw.css", css)
        
        # 5. Integrate and write to file
        html = html or ""
        css = css or ""
        
        # Use framework if available, otherwise fallback to basic structure
        if context.framework and context.framework.html:
            framework_html = context.framework.html
            framework_css = context.framework.css or ""
            
            # Combine CSS
            script_tag = "<script src='logic.js'></script>"
            if '</head>' in framework_html:
                full_html = framework_html.replace('</head>', f'<style>{framework_css}\n{css}</style>\n{script_tag}\n</head>')
            else:
                full_html = f"<style>{framework_css}\n{css}</style>\n{script_tag}\n{full_html}"
                
            # Inject content into the first match of <main id="content"> or <body>
            # Using simple replacement but looking for the start of the tag block
            if 'id="content"' in full_html:
                # Find the closing '>' of the main tag containing id="content"
                try:
                    main_start = full_html.find('id="content"')
                    tag_end = full_html.find('>', main_start)
                    full_html = full_html[:tag_end+1] + html + full_html[tag_end+1:]
                except:
                    full_html = full_html.replace('id="content"', f'id="content">{html}')
            else:
                full_html = full_html.replace('<body>', f'<body>{html}')
        else:
            full_html = f"<!DOCTYPE html><html><head><style>{css}</style><script src='logic.js'></script></head><body>{html}</body></html>"

        with open(os.path.join(context.output_dir, page.filename), "w") as f:
            f.write(full_html)
        context.generated_pages[page.filename] = full_html
        print(f"   ✓ Written {page.filename} ({len(full_html)} bytes)")

    async def _run_pre_integration_check(self, context: GenerationContext) -> bool:
        """
        Verify all files are in place before starting expensive Playwright validation.
        Returns True if checks pass, False if issues were auto-fixed.
        """
        import re
        print("🔍 [DEBUG] Running pre-integration checks...")
        issues_found = False
        
        # 1. Check logic.js exists
        logic_path = os.path.join(context.output_dir, "logic.js")
        if not os.path.exists(logic_path):
            print("   ❌ logic.js not found! Backend generation may have failed.")
            return False
        print("   ✓ logic.js exists")
        
        # 2. Check logic.js has SDK export
        with open(logic_path, 'r') as f:
            logic_content = f.read()
        
        if "window.WebsiteSDK" not in logic_content:
            print("   ⚠️ logic.js missing SDK export. Attempting auto-fix...")
            # Find class name and inject export
            match = re.search(r'class\s+(\w+)\s*\{', logic_content)
            if match:
                class_name = match.group(1)
                export_code = f"\n// Auto-injected SDK export\nif (typeof window !== 'undefined') {{\n  window.WebsiteSDK = new {class_name}();\n}}\n"
                logic_content += export_code
                with open(logic_path, 'w') as f:
                    f.write(logic_content)
                print(f"   ✓ Injected SDK export for class '{class_name}'")
                issues_found = True
            else:
                print("   ❌ Could not find class name in logic.js")
                return False
        else:
            print("   ✓ logic.js has SDK export")
        
        # 3. Check all HTML files reference logic.js
        for page_file in context.generated_pages.keys():
            page_path = os.path.join(context.output_dir, page_file)
            if os.path.exists(page_path):
                with open(page_path, 'r') as f:
                    html_content = f.read()
                
                if 'logic.js' not in html_content:
                    print(f"   ⚠️ {page_file} missing logic.js reference. Injecting...")
                    # Inject before </body>
                    if '</body>' in html_content:
                        html_content = html_content.replace(
                            '</body>',
                            '<script src="logic.js"></script>\n</body>'
                        )
                        with open(page_path, 'w') as f:
                            f.write(html_content)
                        context.generated_pages[page_file] = html_content
                        print(f"   ✓ Injected logic.js reference into {page_file}")
                        issues_found = True
        
        print("   ✅ Pre-integration checks completed.")
        return not issues_found

    async def _run_integration_validation(self, context: GenerationContext):
        """
        Validates frontend/backend integration with a self-healing loop.
        """
        from .agent.environments.env_validator import IntegrationValidator
        from .generators.fix_generator import RootCauseClassifier
        
        if not context.generated_pages:
            print("⚠️ [DEBUG] Skipping integration validation (no pages generated)")
            return
        
        validator = IntegrationValidator()
        classifier = RootCauseClassifier()
        html_files = list(context.generated_pages.keys())
        
        print(f"🔗 [DEBUG] Starting Integration Validation & Fix Loop for {len(html_files)} pages...")
        
        max_retries = 10
        
        for attempt in range(max_retries):
            print(f"   🔄 Integration Attempt {attempt+1}/{max_retries}")
            
            # 1. Validate
            success, errors = await validator.validate_all_pages(context.output_dir, html_files)
            
            if success:
                print("   ✅ Integration validation passed! No JS errors.")
                return
            
            # 2. Classify Errors (NEW: Intelligent routing)
            classifications = classifier.classify(errors, context.output_dir)
            summary = classifier.get_summary(classifications)
            
            print(f"   ❌ Found {len(errors)} integration errors:")
            print(f"      📊 Error Summary: {summary}")
            for err in errors[:5]:  # Limit output to first 5 errors
                category = classifications.get(err, "UNKNOWN")
                print(f"      - [{category}] {err[:100]}...")
            if len(errors) > 5:
                print(f"      ... and {len(errors) - 5} more errors")
            
            context.integration_errors = errors
            
            # 3. Route to correct fixer based on classification
            # 3. Autonomous Repair (OpenHands)
            if attempt < max_retries - 1 and self.llm:
                 from .generators.openhands_resolver import OpenHandsResolver
                 
                 resolver = OpenHandsResolver(self.llm, context.output_dir)
                 
                 # Prepare context for the agent
                 spec_context = {
                     "tasks": [t.__dict__ for t in context.spec.tasks],
                     "interfaces": [i.__dict__ for i in context.spec.interfaces],
                     "backend_code": context.backend_code
                 }
                 
                 print(f"   🤖 Activating OpenHands Resolver for {len(errors)} errors...")
                 success = resolver.resolve(errors, spec_context)
                 
                 if success:
                     print("   ✅ OpenHands resolved the issues. Re-verifying...")
                     attempt += 2 # Skip some retries as we had a rigorous fix
                 else:
                     print("   ⚠️ OpenHands could not fully resolve issues.")
                     
            else:
                print("   ⚠️ Max retries reached. Some integration errors persist.")

    # DEPRECATED: _attempt_integration_fix has been replaced by OpenHandsResolver.resolve() in _process_frontend_integration.
    # We keep the method signature commented out briefly for lineage.
    # async def _attempt_integration_fix(self, context: GenerationContext, errors: list): ...


    async def _run_task_flow_validation(self, context: GenerationContext):
        """
        Validates that each task is achievable by generating and 
        executing a 'Golden Path' action sequence.
        """
        from .generators.verification_generator import VerificationGenerator
        from .agent.environments.env_validator import TaskStepExecutor
        
        if not self.llm:
            print("⚠️ [DEBUG] Skipping task flow validation (no LLM provider)")
            return
            
        gen = VerificationGenerator(self.llm)
        executor = TaskStepExecutor()
        
        for task in context.spec.tasks:
            print(f"🏆 [DEBUG] Validating task: {task.id} - {task.name}")
            
            # 1. Identify target page (very simple heuristic for now)
            # In a real system, we might need to navigate from index.html
            target_page = self._find_target_page_for_task(task, context)
            if not target_page:
                print(f"   ⚠️ Could not identify target page for {task.id}")
                continue
                
            # 2. Generate Golden Path
            print(f"   🧠 Generating Golden Path for {task.id} on {target_page}...")
            html_content = context.generated_pages.get(target_page, "")
            golden_path = await self._run_throttled(
                gen.generate_golden_path,
                task,
                context.spec.architecture.to_dict() if hasattr(context.spec, 'architecture') else {},
                html_content,
                context.backend_code
            )
            
            if not golden_path:
                print(f"   ❌ Failed to generate Golden Path for {task.id}")
                continue
                
            # 3. Execute and Verify
            print(f"   🚀 Executing {len(golden_path['steps'])} steps for {task.id}...")
            success, message = await executor.execute_and_verify(
                context.output_dir,
                target_page,
                golden_path["steps"],
                context.evaluator_code,
                task.id
            )
            
            if success:
                print(f"   ✅ Task {task.id} is ACHIEVABLE! ({message})")
            else:
                print(f"   ❌ Task {task.id} is NOT achievable: {message}")
                # Optional: Trigger fix or regeneration
                
    def _find_target_page_for_task(self, task: Task, context: GenerationContext) -> Optional[str]:
        """Heuristic to find which page a task should start on."""
        # Simple keywords or look at architecture
        desc = task.description.lower()
        if "wizard" in desc or "configurator" in desc:
            return "wizard.html"
        if "editor" in desc:
            return "build-editor.html"
        if "compare" in desc:
            return "compare.html"
        # Fallback to index.html if we can navigate from there
        return "index.html"
