
import os
from ..domain import GenerationContext
from ..interfaces import ISpecGenerator, IBackendGenerator, IFrontendGenerator, IEvaluatorGenerator, IInstrumentationGenerator

class WebGenPipeline:
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
        log_file=None
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
        
        from .logger import PipelineLogger
        self.logger = PipelineLogger(verbose=True)

    def run(self, topic: str, output_dir: str):
        """Executes the full generation pipeline."""
        os.makedirs(output_dir, exist_ok=True)
        context = GenerationContext(seed=topic, output_dir=output_dir)
        
        # Update logger if log_file is set in environment or passed via context (simplified for now)
        # For now, we assume PipelineLogger is initialized once.
        
        # --- Phase 1: Planning ---
        self.logger.phase(f"[{topic}] 1. Planning...")
        # 1.1 Tasks
        from ..domain import WebsiteSpec, PageSpec
        from ..generators.task_generator import TaskConfig
        context.spec = WebsiteSpec(seed=topic)
        
        task_config = TaskConfig(website_type=topic, task_count_min=3, task_count_max=6)
        context.spec.tasks = self.task_gen.generate(topic, task_config)
        self.logger.step(f"Generated {len(context.spec.tasks)} tasks")
        
        context.spec.interfaces = self.interface_designer.design(context.spec) 
        self.logger.step(f"Designed {len(context.spec.interfaces)} interfaces")
        
        # 1.3 Architecture
        context.spec.architecture = self.arch_designer.design(context.spec)
        context.spec.pages = [PageSpec(name=getattr(p, 'name', ''), 
                                     filename=getattr(p, 'filename', ''),
                                     description=f"Page: {getattr(p, 'name', '')}")
                             for p in getattr(context.spec.architecture, 'pages', [])]
        self.logger.step(f"Designed {len(context.spec.pages)} pages")
        
        # --- Phase 2: Data & Backend ---
        self.logger.phase(f"[{topic}] 2. Backend...")
        # 2.1 Data
        context.data = self.data_gen.generate(context.spec)
        self.logger.step(f"Generated {len(context.data)} data collections")
        
        # 2.2 Backend Logic
        raw_logic = self.backend_gen.generate_logic(context.spec)
        
        # 2.3 Instrumentation Analysis
        instr_reqs = self.instr_gen.analyze(context.spec, raw_logic)
        
        # 2.4 Injection
        context.backend_code = self.instr_gen.inject(raw_logic, instr_reqs)
        self.logger.step(f"Generated backend logic ({len(context.backend_code)} bytes)")
        
        with open(os.path.join(output_dir, "logic.js"), "w") as f:
            f.write(context.backend_code)
            
        # --- Phase 3 & 4: Design & Frontend ---
        self.logger.phase(f"[{topic}] 3. Frontend...")
        # 3.1 Design Analysis (Once)
        design_analysis = self.page_designer.analyze_design(topic)
        
        # 3.2 Framework (Header/Footer)
        framework = self.frontend_gen.generate_framework(context.spec, context.spec.architecture)
        
        # Build Arch Map
        arch_pages_map = {p.filename: p for p in getattr(context.spec.architecture, 'pages', [])}
        
        for page in context.spec.pages:
            self.logger.step(f"Processing {page.name}...")
            # 3.3 Page Functionality
            page_design = self.page_designer.design_functionality(page, context.spec)
            
            # 3.4 Page Layout
            layout = self.page_designer.design_layout(page, design_analysis, page_design.components, topic)
            
            # 3.5 HTML
            page_arch = arch_pages_map.get(page.filename, None)
            if not page_arch:
                 page_arch = getattr(context.spec.architecture, 'pages', [None])[0] 
            
            html = self.frontend_gen.generate_html(context.spec, page, page_design, page_arch, framework)
            
            # 3.6 CSS
            css = self.frontend_gen.generate_css(page_design, layout, design_analysis, framework, html)
            
            # Combine
            full_html = f"<style>{css}</style>\n{html}\n<script src='logic.js'></script>"
            
            with open(os.path.join(output_dir, page.filename), "w") as f:
                f.write(full_html)
                
        # --- Phase 5: Evaluation ---
        self.logger.phase(f"[{topic}] 4. Evaluator...")
        context.evaluator_code = self.evaluator_gen.generate(context.spec, instr_reqs, context.backend_code)
        
        with open(os.path.join(output_dir, "evaluator.js"), "w") as f:
            f.write(context.evaluator_code)
            
        # Save Spec
        with open(os.path.join(output_dir, "specs.json"), "w") as f:
            f.write(context.spec.to_json())
            
        self.logger.success(f"[{topic}] Done! Output in {output_dir}")
        return context

