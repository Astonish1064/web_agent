"""
Backend validation for business logic.
=======================================
Runs Node.js tests against generated logic.js.
"""
import os
import subprocess
from typing import Tuple, Optional

from ..config import FileNames


class BackendValidator:
    """Validates backend business logic using Node.js tests."""
    
    def __init__(self, node_timeout: int = 300):
        self.node_timeout = node_timeout
    
    async def validate(self, output_dir: str) -> Tuple[bool, Optional[str]]:
        """
        Runs backend tests and returns (success, error_message).
        
        Args:
            output_dir: Directory containing logic.js and backend_tests.js
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        logic_path = os.path.join(output_dir, FileNames.LOGIC)
        test_path = os.path.join(output_dir, FileNames.BACKEND_TESTS)
        
        if not os.path.exists(logic_path):
            return False, f"Missing {FileNames.LOGIC}"
        
        if not os.path.exists(test_path):
            return False, f"Missing {FileNames.BACKEND_TESTS}"
        
        try:
            result = subprocess.run(
                ["node", test_path],
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=self.node_timeout
            )
            
            if result.returncode != 0:
                error = result.stderr or result.stdout
                return False, f"Test failed: {error[:500]}"
            
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "Test timeout exceeded"
        except FileNotFoundError:
            return False, "Node.js not found"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def check_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Checks JavaScript syntax without running tests.
        
        Args:
            code: JavaScript code to validate
            
        Returns:
            Tuple of (valid: bool, error: Optional[str])
        """
        try:
            result = subprocess.run(
                ["node", "--check", "-e", code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return False, result.stderr
            return True, None
            
        except Exception as e:
            return False, str(e)
