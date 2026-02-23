"""
Planning phase of the pipeline.
================================
Generates tasks, interfaces, and architecture.
"""
import asyncio
from typing import Optional

from ..config import PipelineConfig, IntermediateFiles
from ..logger import PipelineLogger
from ..context import PipelineContext
from ..contracts import SelectorRegistry
from ...domain import Task, PageSpec


class PlanningPhase:
    """
    Executes the planning phase of generation.
    
    This phase:
    1. Generates user tasks from topic
    2. Designs initial architecture
    3. Designs interfaces based on tasks and pages
    4. Refines final architecture with interface assignments
    5. Runs design analysis (optional, parallel)
    """
    
    def __init__(self, generators: dict, config: PipelineConfig, logger: PipelineLogger):
        self.task_gen = generators.get('task_gen')
        self.interface_designer = generators.get('interface_designer')
        self.arch_designer = generators.get('arch_designer')
        self.page_designer = generators.get('page_designer')
        self.config = config
        self.logger = logger
        self.semaphore = asyncio.Semaphore(config.max_concurrency)
    
    async def execute(self, context: PipelineContext) -> SelectorRegistry:
        """
        Executes the planning phase.
        
        Args:
            context: Pipeline context to populate
            
        Returns:
            SelectorRegistry with registered element contracts
        """
        if context.is_planning_complete():
            self.logger.step("Skipping planning phase (already completed)")
            return self._build_registry(context)
            
        # Check for intermediate files to skip partial planning
        from ..config import IntermediateFiles
        final_arch = context.load_intermediate(IntermediateFiles.FINAL_ARCH)
        if final_arch:
             self.logger.step("Skipping planning phase (found existing architecture)")
             context.spec.architecture = final_arch
             context.spec.pages = self._extract_pages(final_arch)
             
             # Ensure tasks and interfaces are also loaded
             tasks = context.load_intermediate(IntermediateFiles.TASKS)
             if tasks:
                 context.spec.tasks = [Task(**t) for t in tasks]
                 
             ifaces = context.load_intermediate(IntermediateFiles.INTERFACES)
             if ifaces:
                 from ...domain import InterfaceDef
                 context.spec.interfaces = [InterfaceDef(**i) for i in ifaces]

             return self._build_registry(context)
        
        # Step 1: Generate tasks
        self.logger.step("Generating user tasks...")
        context.spec.tasks = await self._run_throttled(
            self.task_gen.generate, 
            context.seed,
            self._build_task_config(context.seed)
        )
        self.logger.success(f"Generated {len(context.spec.tasks)} tasks")
        context.save_intermediate(IntermediateFiles.TASKS, 
            [t.__dict__ for t in context.spec.tasks])
        
        # Step 2: Initial architecture (to get pages for interface design)
        self.logger.step("Designing initial architecture...")
        initial_arch = await self._run_throttled(
            self.arch_designer.design, 
            context.spec
        )
        context.spec.pages = self._extract_pages(initial_arch)
        context.save_intermediate(IntermediateFiles.INITIAL_ARCH, initial_arch)
        
        # Step 3: Design interfaces
        self.logger.step("Designing interfaces...")
        context.spec.interfaces = await self._run_throttled(
            self.interface_designer.design, 
            context.spec
        )
        self.logger.success(f"Designed {len(context.spec.interfaces)} interfaces")
        context.save_intermediate(IntermediateFiles.INTERFACES, 
            [i.__dict__ for i in context.spec.interfaces])
        
        # Step 4: Final architecture (with interface assignments)
        self.logger.step("Finalizing architecture...")
        context.spec.architecture = await self._run_throttled(
            self.arch_designer.design, 
            context.spec
        )
        context.spec.pages = self._extract_pages(context.spec.architecture)
        context.save_intermediate(IntermediateFiles.FINAL_ARCH, context.spec.architecture)
        self.logger.success(f"Architecture finalized with {len(context.spec.pages)} pages")
        
        # Step 5: Design analysis (for styling)
        self.logger.step("Running design analysis...")
        design_analysis = await self._run_throttled(
            self.page_designer.analyze_design, 
            context.seed
        )
        context.save_intermediate(IntermediateFiles.DESIGN_ANALYSIS, design_analysis)

        # Step 6: Page Design (Functionality & Layout) - RESTORED FOR PAPER FIDELITY
        # User request: "Add this, because tasks are operations between different web pages"
        self.logger.step("Designing detailed page functionality & layouts...")
        page_designs = {}
        for page in context.spec.pages:
            self.logger.step(f"  Designing page: {page.name}")
            
            # 6.1 Functionality
            # Find assigned interfaces for this page
            # Note: Architecture object structure might vary, trying robust access
            nav_info = {} # Extract navigation info if possible
            
            try:
                func_design = await self._run_throttled(
                    self.page_designer.design_functionality,
                    page, context.spec, nav_info
                )
                
                # 6.2 Layout (needs Analysis)
                layout_design = await self._run_throttled(
                    self.page_designer.design_layout,
                    page, design_analysis, func_design.components, context.seed
                )
                
                page_designs[page.filename] = {
                    "functionality": func_design,
                    "layout": layout_design
                }
            except Exception as e:
                self.logger.warning(f"Failed to design page {page.name}: {e}")
        
        context.page_designs = page_designs
        context.save_intermediate(IntermediateFiles.PAGE_DESIGNS, page_designs)

        
        # Build selector registry from planning outputs
        registry = self._build_registry(context)
        
        return registry
    
    async def _run_throttled(self, func, *args, **kwargs):
        """Runs a function with concurrency limiting."""
        async with self.semaphore:
            return await asyncio.to_thread(func, *args, **kwargs)
    
    def _build_task_config(self, seed: str):
        """Builds task generation configuration."""
        from ...generators.task_generator import TaskConfig
        return TaskConfig(
            website_type=seed, 
            task_count_min=self.config.task_count_min,
            task_count_max=self.config.task_count_max
        )
    
    def _extract_pages(self, architecture) -> list:
        """Extracts PageSpec list from architecture."""
        pages = getattr(architecture, 'pages', [])
        return [
            PageSpec(
                name=getattr(p, 'name', ''),
                filename=getattr(p, 'filename', ''),
                description=f"Page: {getattr(p, 'name', '')}"
            )
            for p in pages
        ]
    
    def _build_registry(self, context: PipelineContext) -> SelectorRegistry:
        """Builds selector registry from tasks and interfaces."""
        return SelectorRegistry.from_tasks(
            context.spec.tasks or [],
            context.spec.interfaces or []
        )
