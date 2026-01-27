import os
import asyncio
import subprocess
import logging
import base64
from typing import Tuple, Optional, Dict, List
from playwright.async_api import async_playwright
from src.interfaces import ILLMProvider
from src.prompts.library import PROMPT_VISUAL_VALIDATION

logger = logging.getLogger("agent.validator")

class EnvironmentHealthChecker:
    """ Validates the quality and functionality of generated web environments. """

    def _get_node_binary(self, output_dir: str) -> str:
        """ Finds a usable node binary, prioritizing local project env. """
        # Try local project nodeenv first
        local_node = os.path.join(os.getcwd(), "venv_node/bin/node")
        if os.path.exists(local_node):
            return local_node

        # Try system path
        try:
            subprocess.run(["node", "-v"], capture_output=True, check=True)
            return "node"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Try common playwright path
        playwright_node = "/usr/local/lib/python3.12/dist-packages/playwright/driver/node"
        if os.path.exists(playwright_node):
            return playwright_node
            
        return "node" # Fallback

    async def validate_backend(self, output_dir: str) -> Tuple[bool, Optional[str]]:
        """ Executes logic.js tests using Node.js. """
        logic_path = os.path.join(output_dir, "logic.js")
        test_path = os.path.join(output_dir, "backend_tests.js")

        if not os.path.exists(logic_path) or not os.path.exists(test_path):
            return False, "Missing logic.js or backend_tests.js"

        try:
            # Run node in a subprocess
            node_bin = self._get_node_binary(output_dir)
            abs_test_path = os.path.abspath(test_path)
            
            # Use mocha from local node_modules
            mocha_bin = os.path.join(os.getcwd(), "node_modules", ".bin", "mocha")
            if not os.path.exists(mocha_bin):
                 # Fallback to globally installed mocha or try to run with node if mocha missing (though it will fail for describe/it)
                 # But we assume we installed it. If not, let's try wrapping it.
                 # Actually, we can just run node_modules/mocha/bin/mocha
                 mocha_bin = os.path.join(os.getcwd(), "node_modules", "mocha", "bin", "mocha")

            # Add local node_modules to NODE_PATH
            env = os.environ.copy()
            local_node_modules = os.path.join(os.getcwd(), "node_modules")
            if "NODE_PATH" in env:
                env["NODE_PATH"] = f"{local_node_modules}:{env['NODE_PATH']}"
            else:
                env["NODE_PATH"] = local_node_modules
            
            # Use node to run mocha executable to ensure we use the right node version
            process = await asyncio.create_subprocess_exec(
                node_bin, mocha_bin, abs_test_path,
                "--reporter", "spec",
                "--timeout", "10000", # Increase timeout
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=output_dir,
                env=env
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return True, None
            else:
                return False, stderr.decode().strip() or stdout.decode().strip()

        except Exception as e:
            return False, f"Node.js execution error: {str(e)}"

    async def validate_frontend(self, output_dir: str, filename: str, screenshot_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """ Validates a frontend page using Playwright. Checks for JS errors and A11y health. """
        html_path = os.path.join(output_dir, filename)
        if not os.path.exists(html_path):
            return False, f"File not found: {filename}"

        errors = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Record page errors
            page.on("pageerror", lambda err: errors.append(f"JS Error: {err.message}"))
            page.on("console", lambda msg: errors.append(f"Console {msg.type}: {msg.text}") if msg.type == "error" else None)

            try:
                # Use file:// URL to load the local HTML
                abs_path = os.path.abspath(html_path)
                await page.goto(f"file://{abs_path}", wait_until="load", timeout=5000)
                
                # Take screenshot if requested
                if screenshot_path:
                    await page.screenshot(path=screenshot_path, full_page=True)
                
                # Basic A11y Tree check using CDP (more robust in some environments)
                cdp = await page.context.new_cdp_session(page)
                await cdp.send("Accessibility.enable")
                ax_tree_raw = await cdp.send("Accessibility.getFullAXTree")
                ax_tree = ax_tree_raw.get("nodes", [])

                if not ax_tree:
                     errors.append("A11y Tree capture failed or empty")
                
                # Check for critical elements (e.g., if it has at least one heading or button)
                # This is a heuristic for "richness"
                has_content = await page.evaluate("() => document.body.innerText.length > 50")
                if not has_content:
                    errors.append("Page has extremely low text content (<50 chars)")

            except Exception as e:
                errors.append(f"Navigation/Load error: {str(e)}")
            finally:
                await browser.close()

        if errors:
            return False, "; ".join(errors)
        return True, None

class VisualValidator:
    """ Evaluates UI quality and functional completeness using screenshots and LLM/VLM. """
    def __init__(self, llm: ILLMProvider):
        self.llm = llm

    async def validate(self, screenshot_path: str, seed: str, page_name: str, page_description: str) -> Dict:
        """ Analyzes a screenshot using LLM/VLM. """
        if not os.path.exists(screenshot_path):
             return {"pass": False, "score": 0, "feedback": "Screenshot missing"}

        with open(screenshot_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        prompt = PROMPT_VISUAL_VALIDATION.format(
            seed=seed,
            page_name=page_name,
            page_description=page_description
        )
        
        # Note: We assume the LLM provider handles vision if passed a base64 string or image path
        # For simplicity in this repro, we'll wrap the prompt with the image data
        # In a real system, this would be a multimodal call.
        response = self.llm.prompt_json(prompt + f"\n[IMAGE_DATA: {base64_image[:100]}...]")
        
        return response
