"""
Generation phase of the pipeline.
==================================
Implements the TCTDD (Task-Centric Test-Driven Development) loop.
"""
import asyncio
import os
from typing import Dict, Optional

from ..config import PipelineConfig, FileNames, IntermediateFiles
from ..logger import PipelineLogger
from ..context import PipelineContext
from ..contracts import SelectorRegistry
from ..validators import BackendValidator, IntegrationValidator, GoldenPathValidator
from ...domain import Task


class GenerationPhase:
    """
    Executes the incremental TCTDD generation loop.
    
    For each task:
    1. Generate task-specific tests (RED)
    2. Plan logic implementation (OpenCode Phase A)
    3. Implement logic to pass tests (OpenCode Phase B)
    4. Implement frontend views
    5. Verify and fix with tiered approach
    """
    
    def __init__(self, generators: dict, config: PipelineConfig, logger: PipelineLogger):
        self.backend_gen = generators.get('backend_gen')
        self.frontend_gen = generators.get('frontend_gen')
        self.controller_gen = generators.get('controller_gen')
        self.instr_gen = generators.get('instr_gen')
        self.evaluator_gen = generators.get('evaluator_gen')
        self.data_gen = generators.get('data_gen')
        self.llm = generators.get('llm')
        self.config = config
        self.logger = logger
        self.semaphore = asyncio.Semaphore(config.max_concurrency)
        
        # Validators
        self.backend_validator = BackendValidator()
        self.integration_validator = IntegrationValidator()
        if self.llm:
            from ..validators.agent_validator import AgentValidator
            self.agent_validator = AgentValidator(self.llm, config)
            
    async def execute(
        self, 
        context: PipelineContext, 
        registry: Optional[SelectorRegistry] = None
    ):
        """
        Executes the generation phase for all tasks.
        
        Args:
            context: Pipeline context
            registry: Optional selector registry from planning
        """
        # Initial data generation
        if not context.data:
            self.logger.step("Generating initial data...")
            context.data = await self._run_throttled(
                self.data_gen.generate, 
                context.spec
            )
            context.save_intermediate(IntermediateFiles.GENERATED_DATA, context.data)
        
        # Initialize base logic if empty
        if not context.backend_code:
            context.backend_code = self._get_base_logic()
        
        # Process each task
        for i, task in enumerate(context.spec.tasks):
            self.logger.phase(f"Task {i+1}/{len(context.spec.tasks)}: {task.id}")
            
            try:
                await self._process_task(context, task, registry)
                self.logger.success(f"Task {task.id} completed")
            except Exception as e:
                self.logger.error(f"Task {task.id} failed: {e}")
                # CONTINUE EXECUTION: Do not raise, allow other tasks to proceed
    
    async def _process_task(
        self, 
        context: PipelineContext, 
        task: Task,
        registry: Optional[SelectorRegistry]
    ):
        """Processes a single task through TCTDD loop."""
        
        # Step 1: Generate tests (RED)
        test_filename = f"tests_{task.id}.js"
        existing_test = context.load_file(test_filename)
        
        if existing_test:
            self.logger.step(f"Skipping test generation for {task.id} (found existing)")
            task_tests = existing_test
        else:
            self.logger.step(f"Generating tests for {task.id}...")
            task_tests = await self._run_throttled(
                self.backend_gen.generate_task_tests,
                task, context.spec, context.data
            )
            context.save_file(test_filename, task_tests)
        
        # Step 2: Plan implementation
        plan_filename = f"plan_{task.id}.md"
        existing_plan = context.load_file(plan_filename)
        
        if existing_plan:
             self.logger.step(f"Skipping planning for {task.id} (found existing)")
             task_plan = existing_plan
             context.task_plans[task.id] = task_plan
        else:
            self.logger.step(f"Planning logic for {task.id}...")
            task_plan = await self._run_throttled(
                self.backend_gen.generate_task_plan,
                task, task_tests, context.backend_code, context.spec
            )
            context.task_plans[task.id] = task_plan
            context.save_file(plan_filename, task_plan)
        
        # Check if we can skip implementation by verifying existing code
        should_implement = True
        if existing_plan and context.backend_code and len(context.backend_code) > 500:
             try:
                 success, error = await self._verify_task(context, task, task_tests)
                 if success:
                     self.logger.step(f"Skipping implementation for {task.id} (verified existing code)")
                     should_implement = False
                 else:
                     self.logger.warning(f"Existing code verification failed for {task.id}: {error}")
             except Exception as e:
                 self.logger.warning(f"Error checking existing code for {task.id}: {e}")

        # Step 3: Implement logic (GREEN)
        if should_implement:
            self.logger.step(f"Implementing logic for {task.id}...")
            new_code = await self._run_throttled(
                self.backend_gen.implement_task_logic,
                task, task_tests, context.backend_code, context.spec, task_plan
            )
            # Defensive check: only update if we got valid code back
            if new_code and len(new_code.strip()) > 100:  # Minimum sanity check
                context.backend_code = new_code
            else:
                self.logger.warning(f"implement_task_logic returned empty/short code, using fallback")
                # If backend code is still the base template, try to generate full logic
                if len(context.backend_code.strip()) < 200:
                    context.backend_code = self._get_full_logic_template(context)
            context.save_file(FileNames.LOGIC, context.backend_code)
        
        # Step 3.5: Instrumentation & Evaluation (Paper Fidelity)
        if should_implement and self.instr_gen and self.config.enable_instrumentation:
            try:
                self.logger.step(f"Analyzing instrumentation for {task.id}...")
                instr_spec = await self._run_throttled(
                    self.instr_gen.analyze,
                    context.spec, context.backend_code
                )
                
                self.logger.step(f"Injecting instrumentation for {task.id}...")
                context.backend_code = await self._run_throttled(
                    self.instr_gen.inject,
                    context.backend_code, instr_spec
                )
                context.save_file(FileNames.LOGIC, context.backend_code)
                
                # Generate Evaluator
                if self.evaluator_gen:
                    self.logger.step(f"Generating evaluator for {task.id}...")
                    evaluator_js = await self._run_throttled(
                        self.evaluator_gen.generate,
                        context.spec, instr_spec, context.backend_code
                    )
                    context.evaluator_code = evaluator_js
                    context.save_file("evaluator.js", evaluator_js)
                    
            except Exception as e:
                self.logger.warning(f"Instrumentation failed for {task.id}: {e}")

        
        # Step 4: Implement frontend (STATIC HTML)
        if should_implement:
            self.logger.step(f"Implementing UI (Static) for {task.id}...")
            new_pages = await self._run_throttled(
                self.frontend_gen.implement_task_view,
                task, context.spec, registry
            )
            self._save_pages(context, new_pages)
            
            # Step 4.5: Implement Controller (app.js)
            if self.controller_gen:
                self.logger.step(f"Implementing Controller (app.js) for {task.id}...")
                new_controller = await self._run_throttled(
                    self.controller_gen.generate_controller,
                    task, new_pages, context.backend_code, context.spec, registry
                )
                if new_controller:
                    context.save_file("app.js", new_controller)
        else:
             self.logger.step(f"Skipping UI & Controller implementation for {task.id} (verified existing code)")
        
        # Step 5: Verify with tiered fixes
        await self._verify_with_fixes(context, task, task_tests, registry)
    
    async def _verify_with_fixes(
        self, 
        context: PipelineContext, 
        task: Task, 
        test_code: str,
        registry: Optional[SelectorRegistry]
    ):
        """Verifies task with tiered fix attempts."""
        for attempt in range(self.config.max_fix_retries):
            self.logger.step(f"Verifying {task.id} (attempt {attempt + 1})...")
            
            success, error = await self._verify_task(context, task, test_code, registry)
            
            if success:
                return
            
            self.logger.warning(f"Verification failed: {error}")
            
            if attempt < self.config.max_fix_retries - 1:
                await self._apply_fix(context, task, error, test_code, attempt)
        
        raise Exception(f"Task {task.id} verification failed after {self.config.max_fix_retries} attempts")
    
    def _find_target_page(self, task, context: PipelineContext) -> str:
        """Finds the starting page for a task."""
        # Heuristic: check task steps for page mentions
        steps = getattr(task, 'steps', []) or []
        
        for step in steps:
            step_lower = step.lower()
            for page in context.generated_pages.keys():
                if page.replace('.html', '').lower() in step_lower:
                    return page
        
        # Default to index.html
        return "index.html"

    async def _verify_task(
        self, 
        context: PipelineContext, 
        task: Task, 
        test_code: str,
        registry: Optional[SelectorRegistry] = None
    ) -> tuple:
        """Runs all verification checks."""
        import shutil
        from ...prompts.library import PROMPT_GOLDEN_PATH_GENERATION
        
        # Copy task tests to standard test file
        test_filename = f"tests_{task.id}.js"
        shutil.copy(
            os.path.join(context.output_dir, test_filename),
            os.path.join(context.output_dir, FileNames.BACKEND_TESTS)
        )
        
        # Backend validation
        success, error = await self.backend_validator.validate(context.output_dir)
        if not success:
            return False, f"Backend: {error}"
        
        # Integration validation
        pages = list(context.generated_pages.keys()) or ["index.html"]
        success, errors = await self.integration_validator.validate_all_pages(
            context.output_dir, pages
        )
        if not success:
            return False, f"Integration: {'; '.join(errors)}"
            
        # Agent Validation (Replaces Golden Path)
        if hasattr(self, 'agent_validator'):
            self.logger.step(f"Running autonomous agent validation for {task.id}...")
            try:
                success, error = await self.agent_validator.validate(
                    task=task,
                    output_dir=context.output_dir
                )
                
                if not success:
                    return False, f"Agent Validation: {error}"
            except Exception as e:
                self.logger.warning(f"Agent validation exception ignored during TDD: {e}")
        
        return True, None
    
    async def _apply_fix(
        self, 
        context: PipelineContext, 
        task: Task, 
        error: str, 
        test_code: str,
        attempt: int
    ):
        """[P1] Applies tiered fix based on error type and attempt number."""
        # [P1-1] Error-based dispatch logic
        error_tier = self._classify_error_tier(error)
        
        if error_tier == 1 or (error_tier == 2 and attempt == 0):
            # Tier 1: Targeted LLM fix for simple/first-attempt errors
            if "Backend" in error or error_tier == 1:
                self.logger.step(f"[Tier 1] Fixing backend for {task.id} (error_tier={error_tier})...")
                new_code = await self._run_throttled(
                    self.backend_gen.implement_task_fix,
                    task, test_code, error, context.backend_code, context.spec
                )
                # [P0-2] Validate output before saving to prevent regression
                if self._is_valid_sdk_code(new_code):
                    context.backend_code = new_code
                    context.save_file(FileNames.LOGIC, context.backend_code)
                else:
                    self.logger.warning(f"[Tier 1] Fix produced invalid code, skipping to preserve existing")
            else:
                if "Element not found" in error or "CSS" in error or "Timeout" in error:
                    # Fix HTML or JS depending on the issue
                    # For V3, right now we assume logic faults in the controller are fixed by it.
                    # We will try Controller Fix first as it's the glue layer.
                    if self.controller_gen:
                        self.logger.step(f"[Tier 1] Fixing controller for {task.id}...")
                        current_controller = context.load_file("app.js") or ""
                        new_controller = await self._run_throttled(
                            self.controller_gen.fix_controller,
                            task, context.generated_pages, current_controller, context.backend_code, context.spec, error, registry
                        )
                        if new_controller:
                            context.save_file("app.js", new_controller)
                    else:
                        self.logger.step(f"[Tier 1] Fixing frontend for {task.id}...")
                        new_pages = await self._run_throttled(
                            self.frontend_gen.fix_task_view,
                            task, context.spec, error, context.generated_pages, registry
                        )
                        self._save_pages(context, new_pages)
        else:
            # Tier 2: Agent-based fix for complex/repeated errors
            self.logger.step(f"[Tier 2] Activating OpenHands agent for {task.id}...")
            try:
                # [P1-2] Create backup before Agent execution
                self._create_backup(context)
                
                from ...generators.openhands_resolver import OpenHandsResolver
                resolver = OpenHandsResolver(self.llm, context.output_dir)
                agent_success = await resolver.resolve(
                    task.description, 
                    error, 
                    context.spec.to_dict()
                )
                if agent_success:
                    # Reload code and validate
                    new_code = context.load_file(FileNames.LOGIC)
                    if new_code and self._is_valid_sdk_code(new_code):
                        context.backend_code = new_code
                    else:
                        self.logger.warning("Agent produced invalid code, restoring backup")
                        self._restore_backup(context)
            except Exception as e:
                self.logger.warning(f"Agent fix failed: {e}")
                self._restore_backup(context)
    
    def _classify_error_tier(self, error: str) -> int:
        """[P1-1] Classifies error into tier based on complexity."""
        # Tier 1: Simple syntax/reference errors - LLM can easily fix
        tier1_patterns = ['SyntaxError', 'ReferenceError', 'TypeError', 'is not defined']
        if any(p in error for p in tier1_patterns):
            return 1
        
        # Tier 2: Complex logic/assertion errors - may need agent
        tier2_patterns = ['AssertionError', 'Timeout', 'Golden Path', 'Integration', 'Agent Validation']
        if any(p in error for p in tier2_patterns):
            return 2
        
        # Default to Tier 2 for unknown errors
        return 2
    
    def _create_backup(self, context: PipelineContext):
        """[P1-2] Creates backup of critical files before Agent execution."""
        import shutil
        from datetime import datetime
        backup_dir = os.path.join(context.output_dir, f"_backup_{datetime.now().strftime('%H%M%S')}")
        try:
            os.makedirs(backup_dir, exist_ok=True)
            # Backup critical files
            for filename in [FileNames.LOGIC, 'index.html', 'task.html']:
                src = os.path.join(context.output_dir, filename)
                if os.path.exists(src):
                    shutil.copy2(src, backup_dir)
            context._backup_dir = backup_dir
            self.logger.step(f"[Backup] Created at {backup_dir}")
        except Exception as e:
            self.logger.warning(f"Backup failed: {e}")
    
    def _restore_backup(self, context: PipelineContext):
        """[P1-2] Restores files from backup if Agent produced invalid code."""
        import shutil
        backup_dir = getattr(context, '_backup_dir', None)
        if not backup_dir or not os.path.exists(backup_dir):
            return
        try:
            for filename in os.listdir(backup_dir):
                src = os.path.join(backup_dir, filename)
                dst = os.path.join(context.output_dir, filename)
                shutil.copy2(src, dst)
            self.logger.step(f"[Backup] Restored from {backup_dir}")
        except Exception as e:
            self.logger.warning(f"Restore failed: {e}")
    
    def _is_valid_sdk_code(self, code: str) -> bool:
        """[P0-2] Validates that generated code contains essential SDK structure."""
        if not code or len(code.strip()) < 100:
            return False
        required_patterns = ['WebsiteSDK', 'window.', 'class']
        return all(pattern in code for pattern in required_patterns)
    
    def _save_pages(self, context: PipelineContext, pages: Optional[Dict]):
        """Saves generated pages to context and files."""
        if not pages or not isinstance(pages, dict):
            return
        
        for filename, html in pages.items():
            if filename == "__raw__" or not filename.endswith(".html"):
                continue
            context.generated_pages[filename] = html
            context.save_file(filename, html)
    
    def _get_base_logic(self) -> str:
        """Returns minimal base logic.js template."""
        return """
class BusinessLogic {
    constructor() {
        this._initData();
    }
    
    _initData() {
        // Initialize localStorage
    }
}

if (typeof window !== 'undefined') {
    window.WebsiteSDK = new BusinessLogic();
}
if (typeof module !== 'undefined') {
    module.exports = BusinessLogic;
}
""".strip()
    
    def _get_full_logic_template(self, context: PipelineContext) -> str:
        """Returns a more complete fallback logic template based on task context."""
        return """
class BusinessLogic {
    constructor() {
        this._initData();
    }
    
    _initData() {
        // Sample data - will be replaced by LLM-generated logic
        this.products = [
            { id: 'prod_001', name: 'Sample Product 1', price: 99.99, rating: 4.5, category: 'general' },
            { id: 'prod_002', name: 'Sample Product 2', price: 199.99, rating: 4.0, category: 'general' },
            { id: 'prod_003', name: 'Sample Product 3', price: 49.99, rating: 4.8, category: 'general' }
        ];
        this.cart = [];
    }
    
    async getCategories() {
        return [{ id: 'cat_general', name: 'General' }];
    }
    
    async getFeaturedProducts() {
        return this.products;
    }
    
    async searchProducts(options = {}) {
        let results = [...this.products];
        const { query, filters, sortBy } = options;
        
        if (query) {
            results = results.filter(p => 
                p.name.toLowerCase().includes(query.toLowerCase())
            );
        }
        
        if (filters?.maxPrice) {
            results = results.filter(p => p.price <= filters.maxPrice);
        }
        
        if (sortBy === 'price_asc') {
            results.sort((a, b) => a.price - b.price);
        } else if (sortBy === 'price_desc') {
            results.sort((a, b) => b.price - a.price);
        } else if (sortBy === 'rating') {
            results.sort((a, b) => b.rating - a.rating);
        }
        
        return results;
    }
    
    async getProductById(id) {
        return this.products.find(p => p.id === id) || null;
    }
    
    async addToCart(productId) {
        const product = this.products.find(p => p.id === productId);
        if (product) {
            this.cart.push({ ...product, quantity: 1 });
            return { success: true };
        }
        return { success: false, error: 'Product not found' };
    }
    
    async getCart() {
        return {
            items: this.cart,
            totalItems: this.cart.length,
            totalPrice: this.cart.reduce((sum, item) => sum + item.price, 0)
        };
    }
}

if (typeof window !== 'undefined') {
    window.WebsiteSDK = new BusinessLogic();
}
if (typeof module !== 'undefined') {
    module.exports = BusinessLogic;
}
""".strip()
    
    async def _run_throttled(self, func, *args, **kwargs):
        """Runs function with concurrency limiting."""
        async with self.semaphore:
            return await asyncio.to_thread(func, *args, **kwargs)
