"""
TDD Tests for PageDesigner (Phase 3)

Tests the IPageDesigner interface and LLMPageDesigner implementation.
Following PROMPT_PAGE_FUNCTIONALITY, PROMPT_DESIGN_ANALYSIS, PROMPT_LAYOUT_DESIGN contracts.
"""
import unittest
from unittest.mock import MagicMock
import json

import sys
sys.path.insert(0, '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro')

from src.interfaces import ILLMProvider


class TestPageDesignerInterface(unittest.TestCase):
    """Tests for IPageDesigner interface."""
    
    def test_interface_exists(self):
        """IPageDesigner interface should be importable."""
        from src.interfaces import IPageDesigner
        self.assertTrue(hasattr(IPageDesigner, 'design_functionality'))
        self.assertTrue(hasattr(IPageDesigner, 'analyze_design'))
        self.assertTrue(hasattr(IPageDesigner, 'design_layout'))
    
    def test_interface_is_abstract(self):
        """IPageDesigner should be abstract."""
        from src.interfaces import IPageDesigner
        with self.assertRaises(TypeError):
            IPageDesigner()


class TestLLMPageDesigner(unittest.TestCase):
    """Tests for LLMPageDesigner implementation."""
    
    def setUp(self):
        self.mock_llm = MagicMock(spec=ILLMProvider)
        
    def _create_functionality_response(self, title, components):
        return json.dumps({
            "title": title,
            "description": "Page description",
            "page_functionality": {
                "core_features": ["Feature 1"],
                "user_workflows": ["Workflow 1"],
                "interactions": ["Click action"],
                "state_logic": "URL handling"
            },
            "components": components
        })
    
    def _create_design_response(self, style, colors):
        return json.dumps({
            "visual_features": {"overall_style": style},
            "color_scheme": {"primary": colors},
            "layout_characteristics": {"grid_system": "12-column"},
            "typography": {"font_families": {"heading": "Inter"}},
            "spacing_system": {"base_unit": "8px"}
        })
    
    def _create_layout_response(self, layouts):
        return json.dumps({
            "chosen_strategies": {"content_arrangement": {"choice": "grid-based"}},
            "overall_layout_description": "Full layout description",
            "component_layouts": layouts
        })
        
    def test_designs_page_components(self):
        """Should design page components from page spec."""
        from src.generators.page_designer import LLMPageDesigner
        
        mock_components = [{"id": "search-form", "type": "search-form", 
                          "functionality": "Search", "data_binding": ["Product"]}]
        self.mock_llm.prompt.return_value = self._create_functionality_response("Home", mock_components)
        
        designer = LLMPageDesigner(self.mock_llm)
        
        page_spec = MagicMock()
        page_spec.name = "Home"
        page_spec.filename = "index.html"
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.data_models = []
        spec.interfaces = []
        
        result = designer.design_functionality(page_spec, spec)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Home")
        self.assertGreater(len(result.components), 0)
        
    def test_defines_workflows(self):
        """Page design should include user workflows."""
        from src.generators.page_designer import LLMPageDesigner
        from types import SimpleNamespace
        
        self.mock_llm.prompt.return_value = self._create_functionality_response("Home", [])
        
        designer = LLMPageDesigner(self.mock_llm)
        
        page_spec = SimpleNamespace(name="Home", filename="index.html")
        
        spec = SimpleNamespace(
            seed="online_bookstore",
            data_models=[],
            interfaces=[]
        )
        
        result = designer.design_functionality(page_spec, spec)
        
        self.assertIn("user_workflows", result.page_functionality)
        
    def test_extracts_color_scheme(self):
        """Should extract color scheme from design."""
        from src.generators.page_designer import LLMPageDesigner
        
        self.mock_llm.prompt.return_value = self._create_design_response("modern", ["#0066cc"])
        
        designer = LLMPageDesigner(self.mock_llm)
        
        result = designer.analyze_design("online_bookstore")
        
        self.assertIn("color_scheme", result.__dict__)
        
    def test_identifies_layout_pattern(self):
        """Should identify layout patterns from design."""
        from src.generators.page_designer import LLMPageDesigner
        
        self.mock_llm.prompt.return_value = self._create_design_response("minimalist", ["#333"])
        
        designer = LLMPageDesigner(self.mock_llm)
        
        result = designer.analyze_design("online_bookstore")
        
        self.assertIn("layout_characteristics", result.__dict__)
        
    def test_creates_component_layouts(self):
        """Should create layouts for each component."""
        from src.generators.page_designer import LLMPageDesigner
        from types import SimpleNamespace
        
        mock_layouts = [{"id": "search-form", "layout_narrative": "Top center", "visual_prominence": "primary"}]
        self.mock_llm.prompt.return_value = self._create_layout_response(mock_layouts)
        
        designer = LLMPageDesigner(self.mock_llm)
        
        page_spec = SimpleNamespace(name="Home")
        
        design_analysis = SimpleNamespace(
            visual_features={"overall_style": "modern"},
            layout_characteristics={"grid_system": "12-column"},
            spacing_system={"base_unit": "8px"}
        )
        
        components = [{"id": "search-form"}]
        
        result = designer.design_layout(page_spec, design_analysis, components, "online_bookstore")
        
        self.assertGreater(len(result.component_layouts), 0)
        
    def test_uses_correct_prompt_for_functionality(self):
        """Should use PROMPT_PAGE_FUNCTIONALITY."""
        from src.generators.page_designer import LLMPageDesigner
        from types import SimpleNamespace
        
        self.mock_llm.prompt.return_value = self._create_functionality_response("Home", [])
        
        designer = LLMPageDesigner(self.mock_llm)
        
        page_spec = SimpleNamespace(name="Home", filename="index.html")
        
        spec = SimpleNamespace(
            seed="online_bookstore",
            data_models=[],
            interfaces=[]
        )
        
        designer.design_functionality(page_spec, spec)
        
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("functional designer", call_args.lower())
        
    def test_handles_malformed_response(self):
        """Should handle malformed JSON gracefully."""
        from src.generators.page_designer import LLMPageDesigner
        from types import SimpleNamespace
        
        self.mock_llm.prompt.return_value = "not valid json"
        
        designer = LLMPageDesigner(self.mock_llm)
        
        page_spec = SimpleNamespace(name="Home", filename="index.html")
        
        spec = SimpleNamespace(
            seed="online_bookstore",
            data_models=[],
            interfaces=[]
        )
        
        result = designer.design_functionality(page_spec, spec)
        
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
