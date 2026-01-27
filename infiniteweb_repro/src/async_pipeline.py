
import asyncio
import os
import json
from .domain import GenerationContext, WebsiteSpec, PageSpec, Task, InterfaceDef, DataModel, Framework
from .generators.task_generator import TaskConfig
from .generators.architecture_designer import Architecture
from .agent.environments.env_validator import EnvironmentHealthChecker

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
        
        # Parallel Step 2: Backend Logic Generation + Frontend Branch
        # Note: We generate the initial logic in parallel with frontend, 
        # but validation (which needs HTML) happens after.
        
        # Skip backend if logic and data are already there
        backend_logic_needed = not context.backend_code or not context.data
        if backend_logic_needed:
            backend_logic_task = asyncio.create_task(self._run_backend_logic_generation(context))
        else:
            print("⏭️ [DEBUG] Skipping backend logic generation (already completed)")
            backend_logic_task = asyncio.create_task(asyncio.sleep(0))
            
        # Frontend logic check (simplified: if we have more than 0 generated pages, we skip framework/pages)
        # Note: In a real scenario, we might want to check IF all pages are there.
        # But for now, if context.generated_pages is populated, we skip.
        frontend_needed = not context.generated_pages
        if frontend_needed:
            frontend_task = asyncio.create_task(self._run_frontend_branch(context, design_analysis))
        else:
            print(f"⏭️ [DEBUG] Skipping frontend branch ({len(context.generated_pages)} pages found)")
            frontend_task = asyncio.create_task(asyncio.sleep(0))
        
        await asyncio.gather(backend_logic_task, frontend_task)
        
        # Step 3: System Validation with Retries (Logic + UI interaction)
        await self._run_system_validation_loop(context)
        
        # Phase 4: Multimodal Validation (Visual + State)
        print("🔍 [DEBUG] Starting multimodal validation...")
        await self._run_multimodal_validation(context)
        
        return context

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
        initial_arch = await self._run_throttled(self.arch_designer.design, context.spec)
        context.spec.pages = [PageSpec(name=getattr(p, 'name', ''), 
                                     filename=getattr(p, 'filename', ''),
                                      description=f"Page: {getattr(p, 'name', '')}")
                             for p in getattr(initial_arch, 'pages', [])]
        self._save_intermediate("2_initial_architecture.json", initial_arch)
        
        # 1.3 Interfaces (now aware of pages)
        print("🔌 [DEBUG] Designing interfaces based on tasks and pages...")
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
            print("🧐 [DEBUG] Validating system integrity (JSDOM + Logic)...")
            success, error = await validator.validate_backend(context.output_dir)
            
            if success:
                print("✅ [DEBUG] System validation passed!")
                break
            else:
                last_error = error
                print(f"❌ [DEBUG] System validation failed: {error}")
                if attempt < max_retries - 1:
                    # Detect error source: backend_tests.js or logic.js
                    is_test_error = "backend_tests.js" in error and (
                        "localStorage is not defined" in error or
                        "SyntaxError" in error or
                        "ReferenceError" in error
                    )
                    
                    if is_test_error:
                        print("🔄 [DEBUG] Error in tests. Attempting to fix backend_tests.js...")
                        # Read current tests
                        with open(test_path, "r") as f:
                            current_tests = f.read()
                        # Fix tests
                        fixed_tests = await self._run_throttled(
                            self.backend_gen.fix_tests,
                            context.spec,
                            current_tests,
                            error
                        )
                        with open(test_path, "w") as f:
                            f.write(fixed_tests)
                        # No need to regenerate tests from prompt since we just fixed them
                    else:
                        print("🔄 [DEBUG] Error in logic. Attempting to fix logic.js...")
                        # Fix logic
                        raw_logic = await self._run_throttled(
                            self.backend_gen.fix_logic, 
                            context.spec, 
                            context.backend_code,
                            error
                        )
                        await self._process_backend_logic(context, raw_logic)
                        # Since logic changed, we MUST regenerate tests to be sure
                        needs_test_regeneration = True
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
            context.spec, page, page_design, page_arch, context.framework
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
