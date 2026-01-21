import unittest
from unittest.mock import patch, MagicMock
import subprocess
import json
import os
from src.runner import NodeRunner, ExecutionResult

class TestNodeRunner(unittest.TestCase):
    def setUp(self):
        self.runner = NodeRunner()

    @patch("subprocess.run")
    def test_run_script_success(self, mock_run):
        """Test that run_script calls node and returns success."""
        # Setup mock behavior
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"success": true, "logs": ["Hello"]}'
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        # Execute
        script = "console.log('Hello');"
        result = self.runner.run(script)

        # Verify subprocess call
        self.assertTrue(mock_run.called)
        args, kwargs = mock_run.call_args
        command = args[0]
        self.assertEqual(command[0], "node")
        # Just check it calls our boot script (we assume it will be passed)
        self.assertIn("boot.js", command[1])
        
        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.logs, ["Hello"])

    @patch("subprocess.run")
    def test_run_script_failure(self, mock_run):
        """Test that run_script handles non-zero exit code."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "SyntaxError: Unexpected token"
        mock_run.return_value = mock_process

        result = self.runner.run("bad code")

        self.assertFalse(result.success)
        self.assertIn("SyntaxError", result.error)

    @patch("subprocess.run")
    def test_run_script_timeout(self, mock_run):
        """Test that run_script handles timeouts."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="node", timeout=10)

        result = self.runner.run("while(true){}", timeout=10)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Execution timed out")

if __name__ == "__main__":
    unittest.main()
