"""
TDD Tests for FrontendGenerator (Phase 4)

Tests the IFrontendGenerator interface and LLMFrontendGenerator implementation.
Following PROMPT_FRAMEWORK_GENERATION, PROMPT_HTML_GENERATION, PROMPT_CSS_GENERATION.
"""
import unittest
from unittest.mock import MagicMock
import json

import sys
sys.path.insert(0, '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro')

from src.interfaces import ILLMProvider


class TestFrontendGeneratorInterface(unittest.TestCase):
    """Tests for IFrontendGenerator interface."""
    
    def test_interface_exists(self):
        """IFrontendGenerator interface should be importable."""
        from src.interfaces import IFrontendGenerator
        self.assertTrue(hasattr(IFrontendGenerator, 'generate_framework'))
        self.assertTrue(hasattr(IFrontendGenerator, 'generate_html'))
        self.assertTrue(hasattr(IFrontendGenerator, 'generate_css'))


class TestLLMFrontendGenerator(unittest.TestCase):
    """Tests for LLMFrontendGenerator implementation."""
    
    def setUp(self):
        self.mock_llm = MagicMock(spec=ILLMProvider)
        
    def _create_framework_response(self, html, css):
        return json.dumps({
            "framework_html": html,
            "framework_css": css
        })
    
    def _create_html_response(self, content):
        return json.dumps({"html_content": content})
        
    def _create_css_response(self, content):
        return json.dumps({"css_content": content})
        
    def test_generates_framework(self):
        """Should generate header/footer framework."""
        from src.generators.frontend_generator import LLMFrontendGenerator
        
        self.mock_llm.prompt.return_value = self._create_framework_response(
            "<nav>Header</nav>", "nav { display: flex; }"
        )
        
        generator = LLMFrontendGenerator(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        
        arch = MagicMock()
        arch.header_links = []
        arch.footer_links = []
        
        result = generator.generate_framework(spec, arch)
        
        self.assertIn("<nav>", result.html)
        self.assertIn("flex", result.css)
        
    def test_generates_html(self):
        """Should generate page HTML content."""
        from src.generators.frontend_generator import LLMFrontendGenerator
        from types import SimpleNamespace
        
        self.mock_llm.prompt.return_value = self._create_html_response("<main>Content</main>")
        
        generator = LLMFrontendGenerator(self.mock_llm)
        
        spec = SimpleNamespace(
            seed="online_bookstore",
            data_models=[]
        )
        
        page_spec = SimpleNamespace(name="Home", filename="index.html")
        page_design = SimpleNamespace(title="Home")
        page_arch = SimpleNamespace(assigned_interfaces=[])
        framework = SimpleNamespace(html="<header></header>", css="")
        
        result = generator.generate_html(spec, page_spec, page_design, page_arch, framework)
        
        self.assertIn("<main>", result)
        
    def test_generates_css(self):
        """Should generate page specific CSS."""
        from src.generators.frontend_generator import LLMFrontendGenerator
        from types import SimpleNamespace
        
        self.mock_llm.prompt.return_value = self._create_css_response(".product { color: red; }")
        
        generator = LLMFrontendGenerator(self.mock_llm)
        
        page_design = SimpleNamespace()
        layout = SimpleNamespace()
        design_analysis = SimpleNamespace()
        framework = SimpleNamespace(html="", css=":root { --primary: blue; }")
        
        result = generator.generate_css(page_design, layout, design_analysis, framework, "<html>")
        
        self.assertIn(".product", result)
        
    def test_uses_correct_prompt_for_framework(self):
        """Should use PROMPT_FRAMEWORK_GENERATION."""
        from src.generators.frontend_generator import LLMFrontendGenerator
        from types import SimpleNamespace
        
        self.mock_llm.prompt.return_value = self._create_framework_response("", "")
        
        generator = LLMFrontendGenerator(self.mock_llm)
        
        spec = SimpleNamespace(seed="online_bookstore")
        arch = SimpleNamespace(header_links=[], footer_links=[])
        
        generator.generate_framework(spec, arch)
        
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("senior web developer", call_args.lower())
        
    def test_handles_malformed_response(self):
        """Should handle malformed JSON gracefully."""
        from src.generators.frontend_generator import LLMFrontendGenerator
        from types import SimpleNamespace
        
        self.mock_llm.prompt.return_value = "not valid json"
        
        generator = LLMFrontendGenerator(self.mock_llm)
        spec = SimpleNamespace(seed="online_bookstore")
        arch = SimpleNamespace(header_links=[], footer_links=[])
        
        result = generator.generate_framework(spec, arch)
        
        self.assertEqual(result.html, "")


if __name__ == '__main__':
    unittest.main()
