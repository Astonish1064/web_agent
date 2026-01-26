
import asyncio
import os
import json
from .domain import GenerationContext, WebsiteSpec, PageSpec
from .generators.task_generator import TaskConfig
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
        """Executes the full generation pipeline asynchronously."""
        abs_output_dir = os.path.abspath(output_dir)
        os.makedirs(abs_output_dir, exist_ok=True)
        context = GenerationContext(seed=topic, output_dir=abs_output_dir)
        context.spec = WebsiteSpec(seed=topic)
        
        # Create intermediates directory
        self.intermediates_dir = os.path.join(abs_output_dir, "intermediates")
        os.makedirs(self.intermediates_dir, exist_ok=True)

        # Parallel Step 1: Planning Chain + Design Analysis
        planning_task = asyncio.create_task(self._run_planning_phase(topic, context))
        design_task = asyncio.create_task(self._run_design_analysis(topic))
        
        await planning_task
        design_analysis = await design_task
        
        # Parallel Step 2: Backend Branch + Frontend Branch (Framework)
        # Note: Frontend Branch will also spawn page generation later, but Framework is the first step.
        backend_task = asyncio.create_task(self._run_backend_branch(context))
        frontend_task = asyncio.create_task(self._run_frontend_branch(context, design_analysis))
        
        await asyncio.gather(backend_task, frontend_task)
        
        # Phase 4: Multimodal Validation (Visual + State)
        print("🔍 [DEBUG] Starting multimodal validation...")
        await self._run_multimodal_validation(context)
        
        return context

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

    async def _run_backend_branch(self, context: GenerationContext):
        """Runs Data -> Logic -> Instr -> Inject in sequence with validation & retries."""
        # 2.1 Data
        print("💾 [DEBUG] Starting data generation...")
        context.data = await self._run_throttled(self.data_gen.generate, context.spec)
        print("💾 [DEBUG] Data generation finished.")
        self._save_intermediate("6_generated_data.json", context.data)
        
        validator = EnvironmentHealthChecker()
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            print(f"⚙️ [DEBUG] Backend generation attempt {attempt + 1}/{max_retries}")
            
            # 2.2 Backend Logic
            raw_logic = await self._run_throttled(self.backend_gen.generate_logic, context.spec)
            self._save_intermediate(f"7_raw_logic_attempt_{attempt+1}.js", raw_logic)
            
            # 2.2.1 Backend Tests (TCTDD)
            print("🧪 [DEBUG] Generating backend integration tests...")
            # Note: generate_tests might need raw_logic and data
            test_code = await self._run_throttled(self.backend_gen.generate_tests, context.spec, raw_logic, context.data)
            
            # 2.3 Instrumentation Analysis
            print("🔍 [DEBUG] Starting instrumentation analysis...")
            instr_reqs = await self._run_throttled(self.instr_gen.analyze, context.spec, raw_logic)
            self._save_intermediate("8_instrumentation_requirements.json", instr_reqs)
            
            # 2.4 Injection
            print("💉 [DEBUG] Starting instrumentation injection...")
            context.backend_code = await self._run_throttled(self.instr_gen.inject, raw_logic, instr_reqs)
            
            # 2.5 Evaluator Generation
            print("🧪 [DEBUG] Starting evaluator generation...")
            context.evaluator_code = await self._run_throttled(
                self.evaluator_gen.generate, context.spec, instr_reqs, context.backend_code
            )
            self._save_intermediate("9_evaluator_uninstrumented.js", context.evaluator_code)
# This is a bit confusing in the original code, but let's save what we have.

            # Temporary write for validation
            logic_path = os.path.join(context.output_dir, "logic.js")
            test_path = os.path.join(context.output_dir, "backend_tests.js")
            eval_path = os.path.join(context.output_dir, "evaluator.js")
            
            with open(logic_path, "w") as f:
                f.write(context.backend_code)
            with open(test_path, "w") as f:
                f.write(test_code)
            with open(eval_path, "w") as f:
                f.write(context.evaluator_code)
                
            # 2.6 Validation
            print("🧐 [DEBUG] Validating backend logic...")
            success, error = await validator.validate_backend(context.output_dir)
            
            if success:
                print("✅ [DEBUG] Backend validation passed!")
                break
            else:
                last_error = error
                print(f"❌ [DEBUG] Backend validation failed: {error}")
                # Optional: Pass last_error back to generate_logic for self-correction
        else:
            print(f"⚠️ [DEBUG] Backend failed after {max_retries} attempts. Last error: {last_error}")
            
        print("✅ [DEBUG] Backend branch complete.")

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
        page_design = await self._run_throttled(
            self.page_designer.design_functionality, page, context.spec
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
        page_arch = arch_pages_map.get(page.filename, None)
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
            
            # Inject content into the first match of <main id="content"> or <body>
            if '<main id="content">' in framework_html:
                full_html = framework_html.replace('<main id="content">', f'<main id="content">{html}')
            else:
                full_html = framework_html.replace('<body>', f'<body>{html}')
                
            # Combine CSS
            full_html = f"<style>{framework_css}\n{css}</style>\n{full_html}\n<script src='logic.js'></script>"
        else:
            full_html = f"<!DOCTYPE html><html><head><style>{css}</style></head><body>{html}<script src='logic.js'></script></body></html>"

        with open(os.path.join(context.output_dir, page.filename), "w") as f:
            f.write(full_html)
        print(f"   ✓ Written {page.filename} ({len(full_html)} bytes)")
