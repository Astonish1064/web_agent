"""
TDD Tests for ArchitectureDesigner (Phase 1.3)

Tests the IArchitectDesigner interface and LLMArchitectDesigner implementation.
Following PROMPT_ARCHITECTURE_DESIGN contract.
"""
import unittest
from unittest.mock import MagicMock
from dataclasses import dataclass
from typing import List, Dict
import json

import sys
sys.path.insert(0, '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro')

from src.interfaces import ILLMProvider


@dataclass
class PageArchitecture:
    """Page with navigation and interface assignments."""
    name: str
    filename: str
    assigned_interfaces: List[str]
    incoming_params: List[str]
    outgoing_connections: List[Dict]
    access_methods: List[Dict]


@dataclass
class Architecture:
    """Complete website architecture."""
    all_pages: List[Dict]
    pages: List[PageArchitecture]
    header_links: List[Dict]
    footer_links: List[Dict] = None


class TestArchitectDesignerInterface(unittest.TestCase):
    """Tests for IArchitectDesigner interface contract."""
    
    def test_interface_exists(self):
        """IArchitectDesigner interface should be importable."""
        from src.interfaces import IArchitectDesigner
        self.assertTrue(hasattr(IArchitectDesigner, 'design'))
    
    def test_interface_is_abstract(self):
        """IArchitectDesigner should be abstract."""
        from src.interfaces import IArchitectDesigner
        with self.assertRaises(TypeError):
            IArchitectDesigner()


class TestLLMArchitectDesigner(unittest.TestCase):
    """Tests for LLMArchitectDesigner implementation."""
    
    def setUp(self):
        self.mock_llm = MagicMock(spec=ILLMProvider)
        
    def _create_response(self, all_pages, pages, header_links):
        """Helper to create mock response."""
        return json.dumps({
            "all_pages": all_pages,
            "pages": pages,
            "header_links": header_links
        })
        
    def test_creates_page_structure(self):
        """Should create page structure from spec."""
        from src.generators.architecture_designer import LLMArchitectDesigner
        
        mock_response = self._create_response(
            all_pages=[{"name": "Home", "filename": "index.html"}],
            pages=[{
                "name": "Home",
                "filename": "index.html",
                "assigned_interfaces": ["searchProducts"],
                "incoming_params": [],
                "outgoing_connections": [{"target": "product.html", "params": {"id": "productId"}}],
                "access_methods": [{"type": "navigation"}]
            }],
            header_links=[{"text": "Home", "url": "index.html"}]
        )
        self.mock_llm.prompt.return_value = mock_response
        
        designer = LLMArchitectDesigner(self.mock_llm)
        
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.interfaces = []
        spec.data_models = []
        
        result = designer.design(spec)
        
        self.assertIsNotNone(result)
        self.assertGreater(len(result.pages), 0)
        
    def test_assigns_interfaces_to_pages(self):
        """Each page should have assigned interfaces."""
        from src.generators.architecture_designer import LLMArchitectDesigner
        
        mock_response = self._create_response(
            all_pages=[{"name": "Home", "filename": "index.html"}],
            pages=[{
                "name": "Home",
                "filename": "index.html",
                "assigned_interfaces": ["searchProducts", "getCategories"],
                "incoming_params": [],
                "outgoing_connections": [],
                "access_methods": [{"type": "navigation"}]
            }],
            header_links=[]
        )
        self.mock_llm.prompt.return_value = mock_response
        
        designer = LLMArchitectDesigner(self.mock_llm)
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.interfaces = []
        spec.data_models = []
        
        result = designer.design(spec)
        
        self.assertGreater(len(result.pages[0].assigned_interfaces), 0)
        
    def test_defines_navigation(self):
        """Should define incoming params and outgoing connections."""
        from src.generators.architecture_designer import LLMArchitectDesigner
        
        mock_response = self._create_response(
            all_pages=[
                {"name": "Home", "filename": "index.html"},
                {"name": "Product", "filename": "product.html"}
            ],
            pages=[
                {
                    "name": "Home",
                    "filename": "index.html",
                    "assigned_interfaces": [],
                    "incoming_params": [],
                    "outgoing_connections": [{"target": "product.html", "params": {"id": "productId"}}],
                    "access_methods": [{"type": "navigation"}]
                },
                {
                    "name": "Product",
                    "filename": "product.html",
                    "assigned_interfaces": ["getProductById"],
                    "incoming_params": ["id"],
                    "outgoing_connections": [],
                    "access_methods": [{"type": "url_param"}]
                }
            ],
            header_links=[{"text": "Home", "url": "index.html"}]
        )
        self.mock_llm.prompt.return_value = mock_response
        
        designer = LLMArchitectDesigner(self.mock_llm)
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.interfaces = []
        spec.data_models = []
        
        result = designer.design(spec)
        
        # Home has outgoing
        self.assertGreater(len(result.pages[0].outgoing_connections), 0)
        # Product has incoming
        self.assertIn("id", result.pages[1].incoming_params)
        
    def test_creates_header_links(self):
        """Should create header navigation links."""
        from src.generators.architecture_designer import LLMArchitectDesigner
        
        mock_response = self._create_response(
            all_pages=[{"name": "Home", "filename": "index.html"}],
            pages=[{
                "name": "Home", "filename": "index.html",
                "assigned_interfaces": [], "incoming_params": [],
                "outgoing_connections": [], "access_methods": []
            }],
            header_links=[
                {"text": "Home", "url": "index.html"},
                {"text": "Categories", "url": "categories.html"}
            ]
        )
        self.mock_llm.prompt.return_value = mock_response
        
        designer = LLMArchitectDesigner(self.mock_llm)
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.interfaces = []
        spec.data_models = []
        
        result = designer.design(spec)
        
        self.assertGreater(len(result.header_links), 0)
        
    def test_uses_correct_prompt(self):
        """Should use PROMPT_ARCHITECTURE_DESIGN from library."""
        from src.generators.architecture_designer import LLMArchitectDesigner
        
        self.mock_llm.prompt.return_value = self._create_response([], [], [])
        
        designer = LLMArchitectDesigner(self.mock_llm)
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.interfaces = []
        spec.data_models = []
        
        designer.design(spec)
        
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("web architect", call_args.lower())
        
    def test_handles_malformed_response(self):
        """Should handle malformed JSON gracefully."""
        from src.generators.architecture_designer import LLMArchitectDesigner
        
        self.mock_llm.prompt.return_value = "not valid json"
        
        designer = LLMArchitectDesigner(self.mock_llm)
        spec = MagicMock()
        spec.seed = "online_bookstore"
        spec.tasks = []
        spec.interfaces = []
        spec.data_models = []
        
        result = designer.design(spec)
        
        # Should return empty architecture
        self.assertEqual(len(result.pages), 0)


if __name__ == '__main__':
    unittest.main()
