
import asyncio
import os
from .domain import GenerationContext, WebsiteSpec, PageSpec
from .generators.task_generator import TaskConfig

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
        max_concurrency=1 # Reduced for stability
    ):
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
        os.makedirs(output_dir, exist_ok=True)
        context = GenerationContext(seed=topic, output_dir=output_dir)
        context.spec = WebsiteSpec(seed=topic)
        
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
        
        return context

    async def _run_throttled(self, func, *args, **kwargs):
        async with self.semaphore:
            return await asyncio.to_thread(func, *args, **kwargs)

    async def _run_planning_phase(self, topic: str, context: GenerationContext):
        """Runs the sequential planning phase."""
        # 1.1 Tasks
        task_config = TaskConfig(website_type=topic, task_count_min=3, task_count_max=6)
        context.spec.tasks = await self._run_throttled(self.task_gen.generate, topic, task_config)
        print(f"📋 [DEBUG] Tasks generated: {len(context.spec.tasks)}")
        
        # 1.2 Interfaces
        context.spec.interfaces = await self._run_throttled(self.interface_designer.design, context.spec)
        print(f"🔌 [DEBUG] Interfaces designed: {len(context.spec.interfaces)}")
        
        # 1.3 Architecture
        context.spec.architecture = await self._run_throttled(self.arch_designer.design, context.spec)
        arch_pages = getattr(context.spec.architecture, 'pages', [])
        print(f"🏗️ [DEBUG] Architecture pages: {len(arch_pages)}")
        for p in arch_pages:
            print(f"    - {getattr(p, 'filename', 'N/A')}: {getattr(p, 'name', 'N/A')}")
        
        # Apply pages
        context.spec.pages = [PageSpec(name=getattr(p, 'name', ''), 
                                     filename=getattr(p, 'filename', ''),
                                     description=f"Page: {getattr(p, 'name', '')}")
                             for p in arch_pages]
        print(f"📄 [DEBUG] Final context.spec.pages count: {len(context.spec.pages)}")

    async def _run_design_analysis(self, topic: str):
        """Runs design analysis."""
        return await self._run_throttled(self.page_designer.analyze_design, topic)

    async def _run_backend_branch(self, context: GenerationContext):
        """Runs Data -> Logic -> Instr -> Inject in sequence (but parallel to frontend)."""
        # 2.1 Data
        context.data = await self._run_throttled(self.data_gen.generate, context.spec)
        
        # 2.2 Backend Logic
        raw_logic = await self._run_throttled(self.backend_gen.generate_logic, context.spec)
        
        # 2.3 Instrumentation Analysis
        instr_reqs = await self._run_throttled(self.instr_gen.analyze, context.spec, raw_logic)
        
        # 2.4 Injection
        context.backend_code = await self._run_throttled(self.instr_gen.inject, raw_logic, instr_reqs)
        
        # Write backend code
        with open(os.path.join(context.output_dir, "logic.js"), "w") as f:
            f.write(context.backend_code)

    async def _run_frontend_branch(self, context: GenerationContext, design_analysis):
        """Runs Framework -> Parallel Page Generation."""
        # 3.2 Framework (Header/Footer)
        context.framework = await self._run_throttled(
            self.frontend_gen.generate_framework, 
            context.spec, 
            context.spec.architecture
        )
        
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
        
        # 2. Layout
        layout = await self._run_throttled(
            self.page_designer.design_layout, 
            page, design_analysis, getattr(page_design, 'components', []), context.seed
        )
        print(f"   ✓ Layout designed for {page.filename}")
        
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
        
        # 4. CSS
        css = await self._run_throttled(
            self.frontend_gen.generate_css, 
            page_design, layout, design_analysis, context.framework, html
        )
        print(f"   ✓ CSS generated for {page.filename}: {len(css) if css else 0} chars")
        
        # 5. Write to file
        html = html or ""
        css = css or ""
        full_html = f"<style>{css}</style>\n{html}\n<script src='logic.js'></script>"
        with open(os.path.join(context.output_dir, page.filename), "w") as f:
            f.write(full_html)
        print(f"   ✓ Written {page.filename} ({len(full_html)} bytes)")
