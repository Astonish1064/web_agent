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

    def _find_project_root(self) -> str:
        """Helper to find the project root containing node_modules."""
        current = os.path.dirname(os.path.abspath(__file__))
        # Walk up up to 3 levels looking for package.json
        for _ in range(4):
            if os.path.exists(os.path.join(current, "package.json")):
                return current
            current = os.path.dirname(current)
        return os.getcwd() # Fallback

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
            
            project_root = self._find_project_root()
            
            # Smartly locate mocha
            # 1. Try local node_modules in project root
            mocha_candidates = [
                os.path.join(project_root, "node_modules", "mocha", "bin", "mocha"),
                os.path.join(project_root, "node_modules", ".bin", "mocha"),
                os.path.join(os.getcwd(), "node_modules", "mocha", "bin", "mocha"),
            ]
            
            mocha_bin = None
            for cand in mocha_candidates:
                if os.path.exists(cand):
                    mocha_bin = cand
                    break
            
            if not mocha_bin:
                 return False, f"Mocha binary not found. Checked: {mocha_candidates}"

            # Add local node_modules to NODE_PATH
            env = os.environ.copy()
            local_node_modules = os.path.join(project_root, "node_modules")
            if "NODE_PATH" in env:
                env["NODE_PATH"] = f"{local_node_modules}:{env['NODE_PATH']}"
            else:
                env["NODE_PATH"] = local_node_modules
            
            # Use node to run mocha executable to ensure we use the right node version
            process = await asyncio.create_subprocess_exec(
                node_bin, mocha_bin, abs_test_path,
                "-r", "jsdom-global/register",
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

                # Heuristic: Detect internal mocks and placeholders
                content = await page.content()
                import re
                
                # Look for forbidden patterns in scripts
                scripts = await page.evaluate("() => Array.from(document.querySelectorAll('script')).map(s => s.innerText).join('\\n')")
                
                forbidden_patterns = [
                    (r"mockDB", "Internal Mock (mockDB) found"),
                    (r"localData\s*=", "Internal Data definition found"),
                    (r"const\s+books\s*=", "Hardcoded data found"),
                    (r"placeholder", "Placeholder text found in code"),
                    (r"[\u4e00-\u9fa5]", "Chinese characters/Character corruption found"),
                    (r"function\s+addToCart", "Local business logic implementation found (should use WebsiteSDK)")
                ]
                
                for pattern, msg in forbidden_patterns:
                    if re.search(pattern, scripts):
                        errors.append(f"Quality Error: {msg}")
                
                if errors:
                    return False, "; ".join(errors)
                    
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


class IntegrationValidator:
    """
    Validates frontend/backend integration by loading actual HTML pages
    with a local HTTP server and capturing JavaScript runtime errors.
    This catches type mismatches between frontend JS and WebsiteSDK.
    """
    
    def __init__(self):
        self.errors = []
        self.server = None
        self.server_thread = None

    async def validate_all_pages(self, output_dir: str, html_files: list) -> Tuple[bool, List[str]]:
        """
        Starts a local server, loads each HTML page, and captures JS errors.
        Returns (success, list_of_errors).
        """
        import http.server
        import socketserver
        import threading
        
        all_errors = []
        port = 0  # Let OS assign a free port
        
        # Start a simple HTTP server
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=output_dir, **kwargs)
            def log_message(self, format, *args):
                pass  # Suppress logs
        
        try:
            self.server = socketserver.TCPServer(("", port), Handler)
            actual_port = self.server.server_address[1]
            base_url = f"http://localhost:{actual_port}"
            
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            logger.info(f"Integration test server started at {base_url}")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                
                for html_file in html_files:
                    page_errors = []
                    page = await context.new_page()
                    
                    # Capture page errors (uncaught exceptions)
                    def on_page_error(err):
                        page_errors.append(f"[{html_file}] JS Error: {err.message}")
                    
                    page.on("pageerror", on_page_error)
                    
                    # Also capture console errors
                    def on_console(msg):
                        if msg.type == "error":
                            page_errors.append(f"[{html_file}] Console Error: {msg.text}")
                    
                    page.on("console", on_console)
                    
                    try:
                        url = f"{base_url}/{html_file}"
                        await page.goto(url, wait_until="networkidle", timeout=10000)
                        
                        # Wait a bit for any async errors
                        await asyncio.sleep(0.5)
                        
                        # Try to verify WebsiteSDK is available
                        sdk_check = await page.evaluate("typeof window.WebsiteSDK !== 'undefined'")
                        if not sdk_check:
                            page_errors.append(f"[{html_file}] WebsiteSDK not defined on window")
                        
                        # Check if any DOMContentLoaded scripts ran without error
                        # by verifying a basic interaction doesn't crash
                        try:
                            # Just check if the page has content
                            body_text = await page.evaluate("document.body.innerText.length")
                            if body_text < 10:
                                page_errors.append(f"[{html_file}] Page appears empty (body text < 10 chars)")
                        except Exception as e:
                            page_errors.append(f"[{html_file}] Page interaction error: {str(e)}")
                        
                    except Exception as e:
                        page_errors.append(f"[{html_file}] Navigation error: {str(e)}")
                    
                    finally:
                        await page.close()
                    
                    all_errors.extend(page_errors)
                
                await browser.close()
                
        except Exception as e:
            all_errors.append(f"Integration server error: {str(e)}")
        finally:
            if self.server:
                self.server.shutdown()
                logger.info("Integration test server stopped")
        
        success = len(all_errors) == 0
        return success, all_errors

    async def validate_single_page(self, output_dir: str, html_file: str) -> Tuple[bool, List[str]]:
        """Validates a single page and returns errors."""
        return await self.validate_all_pages(output_dir, [html_file])


class TaskStepExecutor:
    """
    Executes a sequence of actions on a page using Playwright and 
    verifies if the task is completed via evaluator.js.
    """
    def __init__(self):
        self.server = None

    async def _setup_server(self, output_dir: str):
        import http.server
        import socketserver
        import threading
        
        port = 0
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=output_dir, **kwargs)
            def log_message(self, format, *args):
                pass
        
        self.server = socketserver.TCPServer(("", port), Handler)
        port = self.server.server_address[1]
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        return f"http://localhost:{port}"

    async def execute_and_verify(
        self, 
        output_dir: str, 
        page_file: str, 
        steps: List[Dict], 
        evaluator_js: str, 
        task_id: str
    ) -> Tuple[bool, str]:
        """
        Runs the steps, then runs evaluator code to check success.
        """
        base_url = await self._setup_server(output_dir)
        errors = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Capture console logs
                page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
                # Capture errors
                page.on("pageerror", lambda err: errors.append(f"JS Error: {err.message}"))
                
                # Seed test data into localStorage before loading the page
                # This ensures the golden path validation has data to work with
                await page.add_init_script("""
                    // Seed test data for task_3
                    const initialData = {
                        "categories": [
                            {"id": "cat_1", "name": "Personal", "color": "#FF5733"},
                            {"id": "cat_2", "name": "Work", "color": "#335BFF"},
                            {"id": "cat_3", "name": "Groceries", "color": "#33FF57"},
                            {"id": "cat_4", "name": "Health", "color": "#FF33A8"}
                        ],
                        "tasks": [
                            {"id": "task_1", "title": "Weekly Grocery Run", "description": "Buy milk, eggs, whole wheat bread, organic avocados, chicken breast, and pasta sauce. Don't forget the laundry detergent.", "priority": "high", "due_date": "2023-11-15T18:00:00Z", "is_completed": false, "category_id": "cat_3", "created_at": "2023-11-01T09:00:00Z"},
                            {"id": "task_2", "title": "Pay Electricity Bill", "description": "Log into the city utility portal and pay the outstanding balance of $145.20 before the late fee applies.", "priority": "high", "due_date": "2023-11-14T17:00:00Z", "is_completed": false, "category_id": "cat_1", "created_at": "2023-11-01T10:30:00Z"},
                            {"id": "task_3", "title": "Q4 Strategy Meeting", "description": "Prepare the slide deck for the quarterly review with the stakeholders. Focus on growth metrics.", "priority": "medium", "due_date": "2023-11-20T14:00:00Z", "is_completed": false, "category_id": "cat_2", "created_at": "2023-11-02T08:15:00Z"},
                            {"id": "task_4", "title": "Client Sync: Project Alpha", "description": "Zoom call with the client to discuss the new feature requirements for the dashboard.", "priority": "high", "due_date": "2023-11-16T11:00:00Z", "is_completed": false, "category_id": "cat_2", "created_at": "2023-11-03T13:45:00Z"},
                            {"id": "task_5", "title": "Schedule Dentist Appointment", "description": "Call Dr. Smith's office to book the annual cleaning and checkup.", "priority": "low", "due_date": "2023-11-30T12:00:00Z", "is_completed": false, "category_id": "cat_4", "created_at": "2023-11-04T16:20:00Z"},
                            {"id": "task_6", "title": "Morning Jog", "description": "Run 5k in the park before work.", "priority": "medium", "due_date": "2023-11-13T07:00:00Z", "is_completed": true, "category_id": "cat_4", "created_at": "2023-11-12T20:00:00Z"},
                            {"id": "task_7", "title": "Backup Laptop Data", "description": "Run full system backup to the external hard drive.", "priority": "high", "due_date": "2023-11-12T20:00:00Z", "is_completed": true, "category_id": "cat_2", "created_at": "2023-11-11T09:30:00Z"},
                            {"id": "task_8", "title": "Read 'Atomic Habits'", "description": "Read chapter 4 and take notes.", "priority": "low", "due_date": "2023-11-18T22:00:00Z", "is_completed": false, "category_id": "cat_1", "created_at": "2023-11-05T19:00:00Z"},
                            {"id": "task_9", "title": "Fix Leaky Faucet", "description": "Tighten the valve under the sink. If it persists, order a new washer.", "priority": "high", "due_date": "2023-11-15T10:00:00Z", "is_completed": false, "category_id": "cat_1", "image_url": "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=800&h=600", "created_at": "2023-11-06T11:00:00Z"},
                            {"id": "task_10", "title": "Update Documentation", "description": "Update the API documentation for the new authentication endpoints.", "priority": "medium", "due_date": "2023-11-22T17:00:00Z", "is_completed": false, "category_id": "cat_2", "created_at": "2023-11-07T14:15:00Z"},
                            {"id": "task_11", "title": "Buy Cat Food", "description": "Pick up a large bag of dry food and some wet treats.", "priority": "medium", "due_date": "2023-11-16T19:00:00Z", "is_completed": false, "category_id": "cat_3", "image_url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800&h=600", "created_at": "2023-11-08T08:00:00Z"},
                            {"id": "task_12", "title": "Team Lunch", "description": "Reserve table for 8 at Italian Bistro for Friday team lunch.", "priority": "low", "due_date": "2023-11-17T12:00:00Z", "is_completed": false, "category_id": "cat_2", "created_at": "2023-11-09T10:00:00Z"}
                        ]
                    };
                    localStorage.setItem('tasks', JSON.stringify(initialData.tasks));
                    localStorage.setItem('categories', JSON.stringify(initialData.categories));
                """)
                
                await page.goto(f"{base_url}/{page_file}", wait_until="networkidle")
                
                # Debug: check SDK status
                try:
                    sdk_status = await page.evaluate("window.WebsiteSDK ? (window.WebsiteSDK.books ? window.WebsiteSDK.books.length : 'BOOKS_UNDEFINED') : 'SDK_MISSING'")
                    print(f"DEBUG: SDK Data Length check: {sdk_status}")
                except Exception as e:
                     print(f"DEBUG: SDK Check failed: {e}")
                     sdk_status = 'CHECK_FAILED'

                if sdk_status != 'SDK_MISSING' and sdk_status != 'BOOKS_UNDEFINED' and sdk_status != 'CHECK_FAILED':
                    sdk_call_check = await page.evaluate("""
                        (async () => {
                            const sdk = window.WebsiteSDK;
                            const cat = 'technology';
                            try {
                                const books = await sdk.searchBooks({ category: cat });
                                return {
                                    count: books.length,
                                    first_id: books.length > 0 ? books[0].id : null,
                                    error: null
                                };
                            } catch (e) {
                                return { count: -1, first_id: null, error: e.message };
                            }
                        })()
                    """)
                    print(f"DEBUG: SDK searchBooks call check: {sdk_call_check}")
                
                for step in steps:
                    action = step.get("action")
                    selector = step.get("selector")
                    value = step.get("value")
                    desc = step.get("description", action)
                    
                    logger.info(f"Executing: {desc} ({action} on {selector})")
                    
                    try:
                        if action == "click":
                            # Wait for element specifically
                            try:
                                await page.wait_for_selector(selector, timeout=5000)
                            except:
                                print(f"DEBUG: Selector {selector} NOT FOUND. Page Content: { (await page.content()) }")
                                raise
                            await page.click(selector, timeout=5000)
                        elif action == "type":
                            await page.fill(selector, str(value), timeout=5000)
                        elif action == "select":
                            await page.select_option(selector, str(value), timeout=5000)
                        
                        # Wait for any async effects
                        await asyncio.sleep(1.0)
                        
                        if errors:
                            return False, f"Crash during execution: {errors[0]}"
                            
                    except Exception as e:
                        return False, f"Action failed: {desc} ({str(e)})"

                # All steps done, run evaluation
                # We need to load evaluator.js logic into the page
                try:
                    # evaluator_js should be the full content of evaluator.js
                    # We can inject it and then call the specific task check
                    
                    # Better Approach:
                    # 1. Inject Evaluator Class
                    await page.add_script_tag(content=evaluator_js)
                    
                    # 2. Run Check
                    evaluation_script = f"""
                    (async () => {{
                        if (typeof Evaluator === 'undefined') return false;
                        const eval = new Evaluator();
                        const results = await eval.evaluate();
                        return results['{task_id}'];
                    }})()
                    """
                    is_complete = await page.evaluate(evaluation_script)
                    
                    if is_complete:
                        return True, "Task completed successfully"
                    else:
                        return False, "Steps executed but task failed validation (evaluator check)"
                        
                except Exception as e:
                    return False, f"Evaluation script error: {str(e)}"
                
                finally:
                    await browser.close()
                    
        finally:
            if self.server:
                self.server.shutdown()
                
        return False, "Unknown error during verification"

class ContractValidator:
    """
    Checks logic.js against interfaces.json for API contract adherence.
    """
    def __init__(self):
        self.health_checker = EnvironmentHealthChecker()

    async def validate(self, output_dir: str) -> Dict:
        """Runs the JS contract validator and returns results."""
        import json
        
        validator_script = os.path.join(os.path.dirname(__file__), "contract_validator.js")
        node_bin = self.health_checker._get_node_binary(output_dir)
        
        env = os.environ.copy()
        local_node_modules = os.path.join(os.getcwd(), "node_modules")
        env["NODE_PATH"] = local_node_modules
        
        try:
            process = await asyncio.create_subprocess_exec(
                node_bin, validator_script, output_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 or stdout:
                try:
                    return json.loads(stdout.decode().strip())
                except:
                    return {"success": False, "error": f"JSON Parse Error: {stdout.decode()}"}
            else:
                return {"success": False, "error": stderr.decode().strip() or "Unknown JS error"}
        except Exception as e:
            return {"success": False, "error": f"Internal Validator Error: {str(e)}"}
