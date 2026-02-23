import subprocess
import os
import tempfile
import shutil
from typing import Dict, Optional

class NodeSandbox:
    """
    Safely executes Node.js code in a temporary environment and captures output.
    Used for verifying generated logic and running unit tests.
    """
    
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir or tempfile.mkdtemp(prefix="web_gen_sandbox_")
        
    def cleanup(self):
        """Cleanup the temporary working directory."""
        if os.path.exists(self.working_dir) and "web_gen_sandbox_" in self.working_dir:
            shutil.rmtree(self.working_dir)

    def run_check(self, code: str, filename: str = "check.js") -> Dict:
        """
        Runs a syntax check (node --check) on the provided code.
        """
        temp_path = os.path.join(self.working_dir, filename)
        with open(temp_path, "w") as f:
            f.write(code)
            
        try:
            result = subprocess.run(
                ["node", "--check", temp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stderr": "Syntax check timed out", "stdout": ""}
        except Exception as e:
            return {"success": False, "stderr": str(e), "stdout": ""}

    def run_code(self, code: str, filename: str = "temp_logic.js", env: Optional[Dict] = None) -> Dict:
        """
        Executes the provided code using Node.js and returns results.
        """
        temp_path = os.path.join(self.working_dir, filename)
        with open(temp_path, "w") as f:
            f.write(code)
            
        try:
            # We use a combined env with possible JSDOM or other required globals if mocked
            run_env = os.environ.copy()
            if env:
                run_env.update(env)
                
            result = subprocess.run(
                ["node", temp_path],
                capture_output=True,
                text=True,
                timeout=30,
                env=run_env
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stderr": "Execution timed out (30s limit)", "stdout": ""}
        except Exception as e:
            return {"success": False, "stderr": str(e), "stdout": ""}

    def add_dependency(self, filename: str, content: str):
        """Adds a dependency file (like a mock dataset or interface definition) to the sandbox."""
        path = os.path.join(self.working_dir, filename)
        with open(path, "w") as f:
            f.write(content)
