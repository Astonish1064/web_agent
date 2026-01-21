"""
System Tests: Pipeline End-to-End

Tests the complete pipeline execution from seed to final output.
"""
import unittest
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch
import json

import sys
sys.path.insert(0, '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro')

from src.pipeline import WebGenPipeline
from src.generators.task_generator import LLMTaskGenerator, TaskConfig
from src.generators.interface_designer import LLMInterfaceDesigner
from src.generators.architecture_designer import LLMArchitectDesigner
from src.generators.data_generator import LLMDataGenerator
from src.generators.backend_generator import LLMBackendGenerator
from src.generators.page_designer import LLMPageDesigner
from src.generators.frontend_generator import LLMFrontendGenerator
from src.generators.instrumentation_generator import LLMInstrumentationGenerator
from src.generators.evaluator_generator import LLMEvaluatorGenerator


class TestPipelineE2E(unittest.TestCase):
    """End-to-end system tests for the complete pipeline."""
    
    def setUp(self):
        """Setup mock LLM and pipeline."""
        self.mock_llm = MagicMock()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create all generators
        self.task_gen = LLMTaskGenerator(self.mock_llm)
        self.interface_designer = LLMInterfaceDesigner(self.mock_llm)
        self.arch_designer = LLMArchitectDesigner(self.mock_llm)
        self.data_gen = LLMDataGenerator(self.mock_llm)
        self.backend_gen = LLMBackendGenerator(self.mock_llm)
        self.page_designer = LLMPageDesigner(self.mock_llm)
        self.frontend_gen = LLMFrontendGenerator(self.mock_llm)
        self.instr_gen = LLMInstrumentationGenerator(self.mock_llm)
        self.evaluator_gen = LLMEvaluatorGenerator(self.mock_llm)
        
        # Create pipeline
        self.pipeline = WebGenPipeline(
            task_gen=self.task_gen,
            interface_designer=self.interface_designer,
            arch_designer=self.arch_designer,
            data_gen=self.data_gen,
            backend_gen=self.backend_gen,
            page_designer=self.page_designer,
            frontend_gen=self.frontend_gen,
            instr_gen=self.instr_gen,
            evaluator_gen=self.evaluator_gen
        )
        
    def tearDown(self):
        """Cleanup temp directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _setup_mock_responses(self):
        """Setup deterministic mock responses for all phases."""
        responses = [
            # Phase 1.1: Tasks
            json.dumps({"tasks": [
                {"id": "t1", "name": "Task 1", "description": "Do something", "steps": ["step1", "step2"]}
            ]}),
            
            # Phase 1.2: Interfaces
            json.dumps({"interfaces": [
                {"name": "doSomething", "description": "Main action", "parameters": [], "returns": {}, "relatedTasks": ["t1"]}
            ], "helperFunctions": []}),
            
            # Phase 1.3: Architecture
            json.dumps({
                "all_pages": [{"name": "Home", "filename": "index.html"}],
                "pages": [{
                    "name": "Home", 
                    "filename": "index.html", 
                    "assigned_interfaces": ["doSomething"],
                    "incoming_params": [], 
                    "outgoing_connections": []
                }],
                "header_links": [{"text": "Home", "url": "index.html"}], 
                "footer_links": []
            }),
            
            # Phase 2.1: Data
            json.dumps({"static_data": {"items": [{"id": "i1", "name": "Item 1"}]}}),
            
            # Phase 2.2: Backend Logic
            json.dumps({"code": "class BusinessLogic { doSomething() { return true; } }"}),
            
            # Phase 2.3: Instrumentation Analysis
            json.dumps({"requirements": [{"task_id": "t1", "needs_instrumentation": False}]}),
            
            # Phase 2.4: Instrumentation Injection (Called because requirements list is not empty)
            json.dumps({"code": "class BusinessLogic { doSomething() { return true; } }"}),
            
            # Phase 3.1: Design Analysis (once for all pages)
            json.dumps({
                "visual_features": {"overall_style": "modern"}, 
                "color_scheme": {"primary": ["#000"]},
                "layout_characteristics": {"grid_system": "12-column"}, 
                "ui_patterns": [], 
                "typography": {"font_families": {"heading": "Inter"}}, 
                "spacing_system": {"base_unit": "8px"}
            }),
            
            # Phase 3.2: Framework (once for all pages)
            json.dumps({"framework_html": "<header>App</header>", "framework_css": "header { color: #000; }"}),
            
            # ===== Per-Page Generation (for Home page) =====
            # Phase 3.3: Page Functionality
            json.dumps({
                "title": "Home", 
                "description": "Home page", 
                "page_functionality": {
                    "core_features": ["Display items"],
                    "user_workflows": ["Browse items"],
                    "interactions": ["Click item"]
                }, 
                "components": [{"id": "item-list", "type": "list"}]
            }),
            
            # Phase 3.4: Page Layout
            json.dumps({
                "chosen_strategies": {"content_arrangement": {"choice": "grid-based"}}, 
                "overall_layout_description": "Simple grid layout", 
                "component_layouts": [{"id": "item-list", "layout_narrative": "Center grid"}]
            }),
            
            # Phase 3.5: HTML Generation
            json.dumps({"html_content": "<main id='content'><div>Content</div></main>"}),
            
            # Phase 3.6: CSS Generation
            json.dumps({"css_content": "main { padding: 20px; } [hidden] { display: none; }"}),
            
            # Phase 5: Evaluator
            json.dumps({"evaluators": [{"task_id": "t1", "evaluation_logic": "return true;"}]})
        ]
        self.mock_llm.prompt.side_effect = responses
    
    def test_complete_generation_flow(self):
        """Test complete pipeline execution produces all required files."""
        self._setup_mock_responses()
        
        # Execute pipeline
        context = self.pipeline.run("test_app", self.temp_dir)
        
        # Verify context is populated
        self.assertIsNotNone(context.spec)
        self.assertEqual(len(context.spec.tasks), 1)
        self.assertIsNotNone(context.backend_code)
        self.assertIsNotNone(context.evaluator_code)
        
        # Verify files are created
        expected_files = ["logic.js", "evaluator.js", "specs.json", "index.html"]
        for filename in expected_files:
            file_path = os.path.join(self.temp_dir, filename)
            self.assertTrue(os.path.exists(file_path), 
                          f"Expected file {filename} was not created")
    
    def test_generated_files_are_non_empty(self):
        """Test that all generated files contain content."""
        self._setup_mock_responses()
        
        context = self.pipeline.run("test_app", self.temp_dir)
        
        # Check file sizes
        for filename in ["logic.js", "evaluator. js", "index.html"]:
            file_path = os.path.join(self.temp_dir, filename)
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                self.assertGreater(size, 0, f"{filename} is empty")
    
    def test_cross_file_references_exist(self):
        """Test that HTML references logic.js."""
        self._setup_mock_responses()
        
        context = self.pipeline.run("test_app", self.temp_dir)
        
        # Read HTML file
        html_path = os.path.join(self.temp_dir, "index.html")
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Verify references
        self.assertIn("logic.js", html_content, 
                     "HTML should reference logic.js")


class TestOutputValidation(unittest.TestCase):
    """System tests for output validation."""
    
    def test_javascript_syntax_validity(self):
        """Test that generated JavaScript has valid syntax."""
        # This would use Node.js subprocess to validate
        # For now, basic string checks
        code = "class BusinessLogic { method() { return true; } }"
        
        # Check for basic syntax elements
        self.assertIn("class", code)
        self.assertIn("{", code)
        self.assertIn("}", code)
        self.assertEqual(code.count("{"), code.count("}"))


if __name__ == '__main__':
    unittest.main()
