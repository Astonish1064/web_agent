"""
InfiniteWeb Generation Pipeline - Refactored Orchestrator
==========================================================
Simplified entry point that coordinates generation phases.

This replaces the monolithic 927-line async_pipeline.py with
a clean, modular architecture.
"""
import asyncio
from typing import Optional, Dict, Any

from .pipeline.config import PipelineConfig
from .pipeline.context import PipelineContext
from .pipeline.logger import PipelineLogger
from .pipeline.contracts import SelectorRegistry
from .pipeline.phases import PlanningPhase, GenerationPhase, VerificationPhase


class AsyncWebGenPipelineV2:
    """
    Main pipeline orchestrator (refactored version).
    
    Coordinates three phases:
    1. Planning - Generate tasks, interfaces, architecture
    2. Generation - TCTDD loop for each task
    3. Verification - Final validation
    """
    
    def __init__(
        self, 
        task_gen,
        interface_designer,
        arch_designer,
        data_gen,
        backend_gen,
        page_designer,
        frontend_gen,
        controller_gen,
        instr_gen,
        evaluator_gen,
        llm=None,
        config: Optional[PipelineConfig] = None
    ):
        """
        Initializes the pipeline with generators.
        
        Args:
            task_gen: Task generator
            interface_designer: Interface designer
            arch_designer: Architecture designer
            data_gen: Data generator
            backend_gen: Backend generator
            page_designer: Page designer
            frontend_gen: Frontend generator
            controller_gen: Controller JS generator
            instr_gen: Instrumentation generator
            evaluator_gen: Evaluator generator
            llm: LLM provider
            config: Pipeline configuration (optional)
        """
        self.config = config or PipelineConfig()
        self.logger = PipelineLogger(verbose=self.config.verbose)
        
        # Bundle generators for phases
        self.generators = {
            'task_gen': task_gen,
            'interface_designer': interface_designer,
            'arch_designer': arch_designer,
            'data_gen': data_gen,
            'backend_gen': backend_gen,
            'page_designer': page_designer,
            'frontend_gen': frontend_gen,
            'controller_gen': controller_gen,
            'instr_gen': instr_gen,
            'evaluator_gen': evaluator_gen,
            'llm': llm,
        }
        
        # Initialize phases
        self.planning = PlanningPhase(self.generators, self.config, self.logger)
        self.generation = GenerationPhase(self.generators, self.config, self.logger)
        self.verification = VerificationPhase(self.generators, self.config, self.logger)
    
    async def run(self, topic: str, output_dir: str) -> PipelineContext:
        """
        Executes the full generation pipeline.
        
        Args:
            topic: Website topic/seed
            output_dir: Output directory for generated files
            
        Returns:
            PipelineContext with all generated content
        """
        context = PipelineContext(seed=topic, output_dir=output_dir)
        context.restore()  # Try to resume from existing state
        
        try:
            # Phase 1: Planning
            self.logger.phase(f"Starting Pipeline: {topic}")
            self.logger.phase("Phase 1: Planning")
            registry = await self.planning.execute(context)
            
            # Phase 2: Generation (TCTDD)
            self.logger.phase("Phase 2: Generation (TCTDD)")
            await self.generation.execute(context, registry)
            
            # Phase 3: Verification
            self.logger.phase("Phase 3: Verification")
            results = await self.verification.execute(context, registry)
            context.verification_results = results
            
            # Summary
            self.logger.phase("Pipeline Complete")
            self.logger.success(f"Output: {output_dir}")
            self._print_summary(context, results)
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise
        
        return context
    
    def _print_summary(self, context: PipelineContext, results: Dict[str, Any]):
        """Prints pipeline execution summary."""
        self.logger.info(f"Tasks: {len(context.spec.tasks)}")
        self.logger.info(f"Pages: {len(context.generated_pages)}")
        self.logger.info(f"Interfaces: {len(context.spec.interfaces)}")
        
        if results.get("overall"):
            self.logger.success("All validations passed")
        else:
            self.logger.warning("Some validations failed")


# Alias for backward compatibility
AsyncWebGenPipeline = AsyncWebGenPipelineV2
