import subprocess
import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Any

@dataclass
class ExecutionResult:
    success: bool
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    data: Optional[Any] = None

class NodeRunner:
    def __init__(self, boot_script: str = "src/js_env/boot.js"):
        self.boot_script = boot_script

    def run(self, js_code: str, timeout: int = 30) -> ExecutionResult:
        """
        Executes JavaScript code in a Node.js environment.
        The execution is wrapped by the boot_script which handles context setup.
        """
        
        # Create a temporary file for the user code
        # We write the code to a file so the boot script can load it
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as temp_file:
            temp_file.write(js_code)
            temp_file_path = temp_file.name

        try:
            # Command: node <boot_script> <user_code_path>
            # The boot script is responsible for setting up the environment,
            # requiring the user code, and printing the result as JSON to stdout.
            cmd = ["node", self.boot_script, temp_file_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                # Capture stderr as error
                return ExecutionResult(
                    success=False,
                    error=result.stderr.strip() or f"Process exited with code {result.returncode}",
                    logs=[result.stdout] if result.stdout else []
                )

            # Parse stdout as JSON
            # Expected format: {"success": true, "logs": [], "data": ...}
            try:
                output = json.loads(result.stdout)
                return ExecutionResult(
                    success=output.get("success", False),
                    logs=output.get("logs", []),
                    error=output.get("error"),
                    data=output.get("data")
                )
            except json.JSONDecodeError:
                 return ExecutionResult(
                    success=False,
                    error=f"Failed to parse runner output: {result.stdout}",
                    logs=[result.stdout]
                )

        except subprocess.TimeoutExpired:
            return ExecutionResult(success=False, error="Execution timed out")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
        finally:
            # Cleanup
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
