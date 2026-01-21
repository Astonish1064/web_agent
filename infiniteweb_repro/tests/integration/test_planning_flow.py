"""
Integration Tests: Planning Phase Flow

Tests the data flow and collaboration between:
- TaskGenerator → InterfaceDesigner → ArchitectDesigner
"""
import unittest
from unittest.mock import MagicMock
import json

import sys
sys.path.insert(0, '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro')

from src.generators.task_generator import LLMTaskGenerator, TaskConfig
from src.generators.interface_designer import LLMInterfaceDesigner
from src.generators.architecture_designer import LLMArchitectDesigner
from src.domain import WebsiteSpec


class TestPlanningPhaseIntegration(unittest.TestCase):
    """Integration tests for Planning Phase components."""
    
    def setUp(self):
        """Setup mock LLM provider."""
        self.mock_llm = MagicMock()
        
        # Create generators
        self.task_gen = LLMTaskGenerator(self.mock_llm)
        self.interface_designer = LLMInterfaceDesigner(self.mock_llm)
        self.arch_designer = LLMArchitectDesigner(self.mock_llm)
    
    def test_task_to_interface_data_flow(self):
        """Test that Task Generator output flows correctly to Interface Designer."""
        # Setup: Task Generator produces tasks
        task_response = json.dumps({
            "tasks": [
                {
                    "id": "task_1",
                    "name": "Search Products",
                    "description": "User searches for products",
                    "steps": ["Enter search term", "View results"]
                },
                {
                    "id": "task_2", 
                    "name": "Add to Cart",
                    "description": "Add product to shopping cart",
                    "steps": ["Select product", "Click add to cart"]
                }
            ]
        })
        self.mock_llm.prompt.return_value = task_response
        
        # Execute: Generate tasks
        config = TaskConfig(website_type="online_store", task_count_min=2, task_count_max=5)
        tasks = self.task_gen.generate("online_store", config)
        
        # Verify: Tasks are generated
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, "task_1")
        
        # Setup: Use tasks in spec for Interface Designer
        spec = WebsiteSpec(seed="online_store")
        spec.tasks = tasks
        spec.data_models = []
        spec.pages = []
        
        # Mock Interface Designer response
        interface_response = json.dumps({
            "interfaces": [
                {
                    "name": "searchProducts",
                    "description": "Search for products by query",
                    "parameters": [{"name": "query", "type": "string"}],
                    "returns": {"type": "array"},
                    "relatedTasks": ["task_1"]
                }
            ],
            "helperFunctions": []
        })
        self.mock_llm.prompt.return_value = interface_response
        
        # Execute: Design interfaces
        interfaces = self.interface_designer.design(spec)
        
        # Verify: Interfaces reference tasks
        self.assertEqual(len(interfaces), 1)
        self.assertIn("task_1", interfaces[0].related_tasks)
        
        # Verify: Interface Designer received task data in prompt
        calls = self.mock_llm.prompt.call_args_list
        last_call_args = calls[-1][0][0]
        self.assertIn("task_1", last_call_args)
        self.assertIn("User searches for products", last_call_args)  # Check description
    
    def test_interface_to_architecture_data_flow(self):
        """Test that Interface Designer output flows to Architecture Designer."""
        # Setup: Create spec with tasks and interfaces
        from types import SimpleNamespace
        
        spec = WebsiteSpec(seed="online_store")
        spec.tasks = [
            SimpleNamespace(id="task_1", description="Search products")
        ]
        spec.interfaces = [
            SimpleNamespace(name="searchProducts", parameters=[])
        ]
        spec.data_models = []
        spec.pages = []
        
        # Mock Architecture response
        arch_response = json.dumps({
            "all_pages": [
                {"name": "Home", "filename": "index.html"},
                {"name": "Search", "filename": "search.html"}
            ],
            "pages": [
                {
                    "name": "Search",
                    "filename": "search.html",
                    "assigned_interfaces": ["searchProducts"],
                    "incoming_params": ["query"],
                    "outgoing_connections": []
                }
            ],
            "header_links": [],
            "footer_links": []
        })
        self.mock_llm.prompt.return_value = arch_response
        
        # Execute: Design architecture
        architecture = self.arch_designer.design(spec)
        
        # Verify: Architecture uses interfaces
        self.assertEqual(len(architecture.pages), 1)
        self.assertIn("searchProducts", architecture.pages[0].assigned_interfaces)
        
        # Verify: Architect received interface data
        call_args = self.mock_llm.prompt.call_args[0][0]
        self.assertIn("searchProducts", call_args)
    
    def test_complete_planning_phase_integration(self):
        """Test complete Planning Phase: Tasks → Interfaces → Architecture."""
        # Phase 1: Generate Tasks
        task_response = json.dumps({
            "tasks": [
                {"id": "t1", "name": "Browse", "description": "Browse products", "steps": ["step1"]},
                {"id": "t2", "name": "Purchase", "description": "Buy product", "steps": ["step1"]}
            ]
        })
        self.mock_llm.prompt.return_value = task_response
        
        config = TaskConfig(website_type="shop")
        tasks = self.task_gen.generate("shop", config)
        
        # Phase 2: Design Interfaces
        spec = WebsiteSpec(seed="shop")
        spec.tasks = tasks
        spec.data_models = []
        spec.pages = []
        
        interface_response = json.dumps({
            "interfaces": [
                {"name": "getProducts", "description": "Get all products", 
                 "parameters": [], "returns": {}, "relatedTasks": ["t1"]},
                {"name": "checkout", "description": "Checkout cart",
                 "parameters": [], "returns": {}, "relatedTasks": ["t2"]}
            ],
            "helperFunctions": []
        })
        self.mock_llm.prompt.return_value = interface_response
        interfaces = self.interface_designer.design(spec)
        spec.interfaces = interfaces
        
        # Phase 3: Design Architecture
        arch_response = json.dumps({
            "all_pages": [{"name": "Home", "filename": "index.html"}],
            "pages": [
                {
                    "name": "Home",
                    "filename": "index.html",
                    "assigned_interfaces": ["getProducts", "checkout"],
                    "incoming_params": [],
                    "outgoing_connections": []
                }
            ],
            "header_links": [{"text": "Home", "url": "index.html"}],
            "footer_links": []
        })
        self.mock_llm.prompt.return_value = arch_response
        architecture = self.arch_designer.design(spec)
        
        # Final Verification: Complete spec is valid
        self.assertEqual(len(spec.tasks), 2)
        self.assertEqual(len(spec.interfaces), 2)
        self.assertEqual(len(architecture.pages), 1)
        
        # Verify data consistency
        page = architecture.pages[0]
        interface_names = [i.name for i in spec.interfaces]
        for assigned_interface in page.assigned_interfaces:
            self.assertIn(assigned_interface, interface_names,
                         f"Assigned interface {assigned_interface} not in designed interfaces")


if __name__ == '__main__':
    unittest.main()
