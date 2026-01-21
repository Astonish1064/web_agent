
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# We will need these to mock
from src.domain import WebsiteSpec, PageSpec
from src.generators.architecture_designer import Architecture

class TestAsyncPipeline(unittest.IsolatedAsyncioTestCase):
    
    async def asyncSetUp(self):
        self.patcher = patch('builtins.open', new_callable=MagicMock)
        self.mock_open = self.patcher.start()
        
    async def asyncTearDown(self):
        self.patcher.stop()
    
    async def test_async_planning_and_design_parallelism(self):
        """
        Test that Planning (Task->Interface->Arch) runs in PARALLEL with Design Analysis.
        Total time should be roughly max(planning_time, design_time), not sum.
        """
        # Mock Generators
        mock_task_gen = MagicMock()
        mock_interface_gen = MagicMock()
        mock_arch_gen = MagicMock()
        mock_page_designer = MagicMock()
        
        # Setup mocks to simulate delay
        # Planning chain: Task(0.1s) -> Interface(0.1s) -> Arch(0.1s) = 0.3s total
        mock_task_gen.generate.side_effect = lambda *a: time.sleep(0.1) or []
        mock_interface_gen.design.side_effect = lambda *a: time.sleep(0.1) or []
        mock_arch_gen.design.side_effect = lambda *a: time.sleep(0.1) or Architecture(pages=[])
        
        # Design Analysis: 0.2s
        mock_page_designer.analyze_design.side_effect = lambda *a: time.sleep(0.2) or MagicMock()
        
        # Create Pipeline (to be implemented)
        # Import inside test to allow partial failure if module doesn't exist yet
        try:
            from src.async_pipeline import AsyncWebGenPipeline
        except ImportError:
            self.fail("AsyncWebGenPipeline module not found")
            
        pipeline = AsyncWebGenPipeline(
            task_gen=mock_task_gen,
            interface_designer=mock_interface_gen,
            arch_designer=mock_arch_gen,
            data_gen=MagicMock(),
            backend_gen=MagicMock(),
            page_designer=mock_page_designer,
            frontend_gen=MagicMock(),
            instr_gen=MagicMock(),
            evaluator_gen=MagicMock()
        )
        
        start_time = time.perf_counter()
        
        # Run only the planning/design phase (we need a way to run partial or just check the full run time)
        # For this test, we might implementation a method `run_planning_phase` or test `run` with mocked subsequent steps
        
        # Let's assume we run the whole thing but mock subsequent steps to be instant
        mock_task_gen.generate.return_value = [] # Return empty to skip loops if needed, but we want delays
        # We need the delays to actually happen.
        # But wait, if we use asyncio.to_thread, time.sleep(0.1) will block that thread, not the loop.
        
        # Perform the run
        # We expect run() to be async
        await pipeline.run("test_topic", "test_output")
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Analysis:
        # Sequential would be: 0.1+0.1+0.1 (Planning) + 0.2 (Design) = 0.5s
        # Parallel should be: Max(0.3, 0.2) = 0.3s (approx)
        # We allow some overhead, so assertion should be < 0.45s
        
        print(f"Async Pipeline took {duration:.4f}s")
        self.assertLess(duration, 0.45, "Pipeline did not run Planning and Design in parallel")

    async def test_async_backend_frontend_decoupling(self):
        """
        Test that Backend Branch (Data->Logic->Instr) runs in PARALLEL with Frontend Branch (Framework).
        backend_time = 0.3s
        frontend_time = 0.2s
        Total time should be approx 0.3s (max), not 0.5s (sum).
        """
        mock_task_gen = MagicMock()
        mock_interface_gen = MagicMock()
        mock_arch_gen = MagicMock()
        
        # Fast planning
        mock_task_gen.generate.return_value = []
        mock_interface_gen.design.return_value = []
        mock_arch_gen.design.return_value = Architecture(pages=[])
        
        mock_data_gen = MagicMock()
        mock_backend_gen = MagicMock()
        mock_instr_gen = MagicMock()
        mock_frontend_gen = MagicMock()
        mock_page_designer = MagicMock()
        
        # Mocks with delays
        # Backend Branch: Data(0.1) -> Logic(0.1) -> Instr(0.1) = 0.3s
        mock_data_gen.generate.side_effect = lambda *a: time.sleep(0.1) or []
        mock_backend_gen.generate_logic.side_effect = lambda *a: time.sleep(0.1) or "code"
        mock_instr_gen.analyze.side_effect = lambda *a: time.sleep(0.1) or MagicMock()
        mock_instr_gen.inject.return_value = "injected_code"
        
        # Frontend Branch: Framework(0.2)
        mock_frontend_gen.generate_framework.side_effect = lambda *a: time.sleep(0.2) or MagicMock()
        # Fast design analysis
        mock_page_designer.analyze_design.return_value = MagicMock()

        try:
            from src.async_pipeline import AsyncWebGenPipeline
        except ImportError:
            self.fail("AsyncWebGenPipeline module not found")
            
        pipeline = AsyncWebGenPipeline(
            task_gen=mock_task_gen,
            interface_designer=mock_interface_gen,
            arch_designer=mock_arch_gen,
            data_gen=mock_data_gen,
            backend_gen=mock_backend_gen,
            page_designer=mock_page_designer, # fast
            frontend_gen=mock_frontend_gen,
            instr_gen=mock_instr_gen,
            evaluator_gen=MagicMock()
        )
        
        start_time = time.perf_counter()
        await pipeline.run("test_topic", "test_output")
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        print(f"Decoupling Test took {duration:.4f}s")
        # Allow overhead. Should be clearly < 0.5s
        self.assertLess(duration, 0.45, "Backend and Frontend branches did not run in parallel")
        
        # Verify methods were actually called
        mock_data_gen.generate.assert_called_once()
        mock_backend_gen.generate_logic.assert_called_once()
        mock_instr_gen.analyze.assert_called_once()
        mock_frontend_gen.generate_framework.assert_called_once()

    async def test_async_page_generation_concurrency(self):
        """
        Test that multiple pages are generated concurrently.
        3 pages, each taking 0.1s.
        Total time for pages should be approx 0.1s, not 0.3s.
        Plus planning overhead.
        """
        mock_arch_gen = MagicMock()
        # 3 pages
        pages = [
            PageSpec(name="P1", filename="p1.html", description=""),
            PageSpec(name="P2", filename="p2.html", description=""),
            PageSpec(name="P3", filename="p3.html", description="")
        ]
        # Architecture design returns these pages
        mock_arch_gen.design.return_value = Architecture(pages=pages)
        
        mock_task_gen = MagicMock()
        mock_task_gen.generate.return_value = []
        mock_interface_gen = MagicMock()
        mock_interface_gen.design.return_value = []
        
        mock_frontend_gen = MagicMock()
        mock_page_designer = MagicMock()
        
        # Simulate delays
        # Framework: 0.05s
        mock_frontend_gen.generate_framework.side_effect = lambda *a: time.sleep(0.05) or MagicMock()
        
        # Page Pipeline: Design(0.1s per page) -> Layout -> HTML -> CSS
        # We simulate the whole page pipeline taking 0.1s
        mock_page_designer.design_functionality.side_effect = lambda *a: time.sleep(0.1) or MagicMock()
        
        try:
            from src.async_pipeline import AsyncWebGenPipeline
        except ImportError:
            self.fail("AsyncWebGenPipeline module not found")
            
        pipeline = AsyncWebGenPipeline(
            task_gen=mock_task_gen,
            interface_designer=mock_interface_gen,
            arch_designer=mock_arch_gen,
            data_gen=MagicMock(),
            backend_gen=MagicMock(),
            page_designer=mock_page_designer,
            frontend_gen=mock_frontend_gen,
            instr_gen=MagicMock(),
            evaluator_gen=MagicMock()
        )
        
        start_time = time.perf_counter()
        await pipeline.run("test_topic", "test_output")
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        print(f"Page Concurrency Test took {duration:.4f}s")
        
        # Breakdown:
        # Planning: tiny
        # Backend: tiny (mocked instant)
        # Frontend Branch: Framework(0.05) + Parallel Pages(0.1) = 0.15s
        # Sequential Pages would be: Framework(0.05) + 3*0.1 = 0.35s
        
        self.assertLess(duration, 0.25, "Pages did not generate concurrently")
        
        # Assert called 3 times
        self.assertEqual(mock_page_designer.design_functionality.call_count, 3)


