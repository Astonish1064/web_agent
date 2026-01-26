
import unittest
import asyncio
import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, AsyncMock, patch

from src.agent.environments.playwright_env import PlaywrightEnvironment
from src.agent.monitoring.trajectory_recorder import TrajectoryRecorder
from src.domain import Task
from src.agent.domain import Action, Observation

class TestAgentMockExploration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use a fixed directory for manual inspection
        self.output_dir = os.path.abspath("output/mock_test_results")
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
            
        self.website_dir = os.path.join(self.output_dir, "website")
        os.makedirs(self.website_dir, exist_ok=True)
        
        # Test Data
        self.task = Task(
            id="test_task_1",
            description="Test task description",
            complexity=1,
            required_steps=["Step 1", "Step 2"]
        )
        
        # Initialize Recorder
        self.recorder = TrajectoryRecorder(self.output_dir)
        self.recorder.start(self.task, self.website_dir)

    async def asyncTearDown(self):
        # Do not delete artifacts so user can inspect them
        pass

    @patch('src.agent.environments.playwright_env.async_playwright')
    @patch('src.agent.environments.playwright_env.ActionExecutor')
    @patch('src.agent.environments.playwright_env.LocalWebServer')
    @patch('src.agent.environments.playwright_env.WebEvaluator')
    async def test_mock_exploration_cycle(self, MockEvaluator, MockServer, MockExecutor, MockPlaywright):
        """
        Simulate an agent exploration loop with mocks to verify:
        1. Instrumentation capture
        2. Task evaluation
        3. Trajectory recording
        """
        
        # --- 1. Setup Environment Mocks ---
        
        # Mock Browser/Page
        mock_page = AsyncMock()
        mock_page.url = "http://localhost:8000/index.html"
        mock_page.title = AsyncMock(return_value="Test Page")
        mock_page.screenshot = AsyncMock(return_value=b"fake_png_bytes")
        mock_page.content = AsyncMock(return_value="<html></html>")
        
        # Mock Context
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.cookies = AsyncMock(return_value=[])
        
        # Mock CDP Session for A11y (Optional, can just fail gracefully)
        mock_cdp = AsyncMock()
        mock_cdp.send = AsyncMock(return_value={"nodes": []}) # formatted for A11yProcessor
        mock_context.new_cdp_session = AsyncMock(return_value=mock_cdp)

        # Mock Browser
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        
        # Mock Playwright Object
        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        MockPlaywright.return_value.start = AsyncMock(return_value=mock_pw_instance)
        
        # Mock Action Executor
        mock_executor_instance = MockExecutor.return_value
        mock_executor_instance.execute = AsyncMock(return_value=True) # Successfully executed action
        
        # Mock Evaluator
        mock_evaluator_instance = MockEvaluator.return_value
        # Scenario: 
        # Step 1: Reward 0.0
        # Step 2: Reward 1.0 (Success)
        mock_evaluator_instance.evaluate_task = AsyncMock(side_effect=[0.0, 1.0])
        
        # Mock Instrumentation (page.evaluate)
        # We need to mock different returns for successive calls
        # 1. Start (Reset) -> {}
        # 2. After Step 1 -> {"state": "step1_done"}
        # 3. After Step 2 -> {"state": "step2_done", "final": True}
        
        async def mock_evaluate_side_effect(script, *args):
            if "window.__instrumentation" in script:
                # Determine return based on call count or external state
                # Using a simple counter on the mock itself for simplicity
                count = mock_page.evaluate.call_count
                if count == 1: # Reset
                    return {}
                elif count == 2: # Step 1
                    return {"state": "step1_done"}
                elif count >= 3: # Step 2
                    return {"state": "step2_done", "final": True}
            return None

        mock_page.evaluate = AsyncMock(side_effect=mock_evaluate_side_effect)

        # --- 2. Initialize Environment ---
        
        env = PlaywrightEnvironment(headless=True)
        # Reset triggers env start
        obs_initial = await env.reset(self.website_dir, self.task)
        
        self.assertEqual(obs_initial.instrumentation_state, {})
        
        # --- 3. Execute Step 1 (Action: Click) ---
        
        action_1 = Action(
            type="click",
            target="button.start",
            reasoning="Starting the task"
        )
        
        obs_1, reward_1, done_1, info_1 = await env.step(action_1)
        
        # Verify Step 1
        self.assertEqual(reward_1, 0.0)
        self.assertFalse(done_1)
        self.assertEqual(obs_1.instrumentation_state, {"state": "step1_done"})
        
        # Record Step 1
        self.recorder.record(action_1, obs_initial, obs_1, reward_1, done_1, info_1)
        
        # --- 4. Execute Step 2 (Action: Type -> Finish) ---
        
        action_2 = Action(
            type="type",
            target="input.name",
            value="WebAgent",
            reasoning="Entering name"
        )
        
        obs_2, reward_2, done_2, info_2 = await env.step(action_2)
        
        # Verify Step 2 (Success)
        self.assertEqual(reward_2, 1.0)
        self.assertTrue(done_2) # Reward >= 1.0 triggers done
        self.assertEqual(obs_2.instrumentation_state, {"state": "step2_done", "final": True})
        
        # Record Step 2
        self.recorder.record(action_2, obs_1, obs_2, reward_2, done_2, info_2)
        
        # --- 5. Finalize Recording ---
        
        self.recorder.finalize(success=True, total_reward=1.0)
        
        
        # --- 6. Verification of Artifacts ---
        
        traj_dir = self.recorder.traj_dir
        jsonl_path = os.path.join(traj_dir, "traj.jsonl")
        summary_path = os.path.join(traj_dir, "summary.json")
        
        self.assertTrue(os.path.exists(jsonl_path), "traj.jsonl should exist")
        self.assertTrue(os.path.exists(summary_path), "summary.json should exist")
        
        # Check JSONL contents
        with open(jsonl_path, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)
            
            # Entry 1
            entry_1 = json.loads(lines[0])
            self.assertEqual(entry_1["step_num"], 1)
            self.assertEqual(entry_1["action"]["type"], "click")
            self.assertEqual(entry_1["instrumentation"], {"state": "step1_done"})
            self.assertEqual(entry_1["reward"], 0.0)
            
            # Entry 2
            entry_2 = json.loads(lines[1])
            self.assertEqual(entry_2["step_num"], 2)
            self.assertEqual(entry_2["action"]["type"], "type")
            self.assertEqual(entry_2["instrumentation"], {"state": "step2_done", "final": True})
            self.assertEqual(entry_2["reward"], 1.0)
            self.assertTrue(entry_2["done"])

        # Check Screenshots
        # The recorder generates filenames based on timestamp so we just check count
        png_files = [f for f in os.listdir(traj_dir) if f.endswith('.png')]
        self.assertEqual(len(png_files), 2)

if __name__ == "__main__":
    unittest.main()
