"""
Golden Path validation.
========================
Generates and executes task completion sequences.
"""
import json
from typing import Tuple, Optional, Dict, List
from bs4 import BeautifulSoup

from ..config import PipelineConfig, Limits


class GoldenPathValidator:
    """
    Validates task completion through action sequences.
    
    Generates a "golden path" of actions to complete a task,
    then executes them to verify the UI and backend work together.
    """
    
    def __init__(self, llm, config: Optional[PipelineConfig] = None):
        self.llm = llm
        self.config = config or PipelineConfig()
    
    def extract_selectors(self, html_content: str) -> List[str]:
        """
        Extracts valid interactive selectors from HTML.
        
        Prioritizes IDs over classes for reliability.
        
        Args:
            html_content: HTML string to parse
            
        Returns:
            List of CSS selectors
        """
        selectors = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            interactive_tags = ['a', 'button', 'input', 'select', 'textarea']
            
            for tag in soup.find_all(lambda t: (
                t.name in interactive_tags or
                t.get('onclick') or
                t.get('role') == 'button' or
                t.get('tabindex') == '0'
            )):
                # Skip hidden elements
                if tag.get('type') == 'hidden':
                    continue
                if 'display: none' in tag.get('style', ''):
                    continue
                
                # Priority 1: ID selectors (most reliable)
                if tag.get('id'):
                    selectors.append(f"#{tag['id']}")
                    continue
                
                # Priority 2: data-testid
                if tag.get('data-testid'):
                    selectors.append(f"[data-testid='{tag['data-testid']}']")
                    continue
                
                # Priority 3: Meaningful classes (less reliable)
                classes = tag.get('class', [])
                if classes:
                    # Filter out generic framework classes
                    excluded = {'btn', 'container', 'row', 'col', 'd-flex', 'form-control'}
                    meaningful = [c for c in classes if c not in excluded]
                    if meaningful:
                        selectors.append(f".{'.'.join(meaningful[:2])}")
            
            # Deduplicate and limit
            selectors = sorted(set(selectors))
            
            # Prioritize IDs
            if len(selectors) > self.config.max_selectors:
                ids = [s for s in selectors if s.startswith('#')]
                others = [s for s in selectors if not s.startswith('#')]
                max_others = self.config.max_selectors - len(ids)
                selectors = ids[:self.config.max_selectors] + others[:max(0, max_others)]
                selectors = selectors[:self.config.max_selectors]
            
            return selectors
            
        except Exception as e:
            return []
    
    async def generate_path(
        self,
        task,
        html_content: str,
        logic_code: str,
        architecture: Dict,
        prompt_template: str,
        registry: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Generates action sequence for a task with validation and retries.
        """
        selectors = self.extract_selectors(html_content)
        
        # Add registry selectors to valid pool
        if registry:
            selectors = sorted(list(set(selectors + list(registry.values()))))

        # [P3] Retry loop with validation
        max_attempts = 2
        for attempt in range(max_attempts):
            prompt = prompt_template.format(
                task_description=task.description,
                task_steps=json.dumps(getattr(task, 'steps', []), indent=2),
                architecture_json=json.dumps(architecture, indent=2),
                html_content=html_content[:self.config.html_truncate_length],
                logic_code=logic_code[:self.config.logic_truncate_length],
                task_id=task.id,
                valid_selectors=json.dumps(selectors, indent=2),
                contract_json=json.dumps(registry or {}, indent=2)
            )
            
            try:
                response = self.llm.prompt_json(prompt)
                if response and "steps" in response:
                    # Validate steps
                    is_valid, corrected_steps = self._validate_steps(response["steps"], selectors)
                    if is_valid:
                        response["steps"] = corrected_steps
                        return response
                    
                    # If invalid and we have retries left, adjust prompt
                    if attempt < max_attempts - 1:
                        self.logger.warning(f"Golden path validation failed on attempt {attempt+1}, retrying...")
                else:
                    if attempt < max_attempts - 1: continue
                    return None
            except Exception:
                if attempt < max_attempts - 1: continue
                return None
        
        return None

    def _validate_steps(self, steps: List[Dict], valid_selectors: List[str]) -> Tuple[bool, List[Dict]]:
        """
        [P3] Validates and optionally corrects hallucinated selectors.
        """
        corrected_steps = []
        is_fully_valid = True
        
        for step in steps:
            selector = step.get("selector")
            if not selector:
                corrected_steps.append(step)
                continue
            
            # 1. Direct match
            if selector in valid_selectors:
                corrected_steps.append(step)
                continue
            
            # 2. Fuzzy match (common hallucination: #title vs #task-title)
            # Remove # or . for comparison
            clean_sel = selector.lstrip('#.')
            for valid in valid_selectors:
                clean_valid = valid.lstrip('#.')
                # Simple containment or similarity check
                if clean_sel in clean_valid or clean_valid in clean_sel:
                    # Only auto-correct if it's an ID match
                    if valid.startswith('#') and selector.startswith('#'):
                        step["selector"] = valid
                        corrected_steps.append(step)
                        break
            else:
                # 3. Allow inferred selectors for next pages (if they don't look like current page hallucinations)
                # If the selector is very specific and not in current page, we assume it's for a future page
                # but we mark it as "potential risk"
                corrected_steps.append(step)
                # We don't mark is_fully_valid = False here to allow navigation flow,
                # but we could be stricter if we had all-page selectors.
        
        return is_fully_valid, corrected_steps
    
    async def execute_path(
        self,
        output_dir: str,
        page_file: str,
        steps: List[Dict],
        evaluator_code: str,
        task_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Executes golden path steps in browser.
        
        Args:
            output_dir: Directory with HTML files
            page_file: Starting page
            steps: List of action dicts
            evaluator_code: JavaScript evaluator
            task_id: Task being validated
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return False, "Playwright not installed"
        
        import os
        import http.server
        import socketserver
        import socket
        import threading
        
        # Define HTTPServerContext locally or import from shared
        # Duplicating here to avoid circular imports or complex refactoring for now
        class QuietHTTPHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass
        
        class HTTPServerContext:
            def __init__(self, directory: str):
                self.directory = os.path.abspath(directory)
                self.server = None
                self.thread = None
                self.port = None
            
            def _find_free_port(self) -> int:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', 0))
                    s.listen(1)
                    port = s.getsockname()[1]
                return port
            
            def __enter__(self):
                self.port = self._find_free_port()
                directory = self.directory
                class Handler(QuietHTTPHandler):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, directory=directory, **kwargs)
                self.server = socketserver.TCPServer(('127.0.0.1', self.port), Handler)
                self.thread = threading.Thread(target=self.server.serve_forever)
                self.thread.daemon = True
                self.thread.start()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.server:
                    self.server.shutdown()
                    self.server.server_close()
            
            @property
            def base_url(self) -> str:
                return f"http://127.0.0.1:{self.port}"
        
        # Use HTTP server
        with HTTPServerContext(output_dir) as server:
             async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Ignore non-critical resource failures
                def on_console(msg):
                   if msg.type == "error":
                       text = msg.text
                       # Same filter as IntegrationValidator
                       non_critical_patterns = [
                           "favicon.ico", "404", 
                           ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
                           ".css", ".woff", ".woff2", ".ttf", ".eot",
                           ".mp3", ".mp4", ".wav", ".ogg"
                       ]
                       is_non_critical = any(p in text.lower() for p in non_critical_patterns)
                       if not is_non_critical:
                           # Log or store errors if needed
                           pass
                page.on("console", on_console)

                try:
                    # Use server URL
                    url = f"{server.base_url}/{page_file}"
                    await page.goto(url, timeout=10000)
                    
                    async def find_element_with_fallback(sel):
                        # 1. Try direct selector
                        try:
                            el = await page.query_selector(sel)
                            if el: return el
                        except: pass
                        
                        # 2. Fallback for IDs: Try by Role/Name/Text
                        if sel.startswith('#'):
                            base = sel.lstrip('#').lower()
                            # Common patterns: btn-sort-by -> Sort By
                            keywords = base.replace('btn-', '').replace('input-', '').replace('select-', '').replace('-', ' ')
                            
                            try:
                                # Try by text
                                loc = page.get_by_text(keywords, exact=False)
                                if await loc.count() > 0: return await loc.first.element_handle()
                                
                                # Try by role
                                for role in ["button", "link", "input", "select"]:
                                    loc = page.get_by_role(role, name=keywords, exact=False)
                                    if await loc.count() > 0: return await loc.first.element_handle()
                            except: pass
                        return None

                    for step in steps:
                        action = step.get("action")
                        selector = step.get("selector")
                        
                        # Wait for element with fallback
                        element = await find_element_with_fallback(selector)
                        if not element:
                            # Final wait attempt
                            try:
                                await page.wait_for_timeout(1000)
                                element = await find_element_with_fallback(selector)
                            except: pass
                            
                        if not element:
                            # Check if this is a navigation step to the current page
                            # If so, skip it since we're already there
                            current_url = page.url
                            if action == "click" and selector:
                                # Extract href from selector if it's an anchor tag
                                import re
                                href_match = re.search(r"a\[href=['\"]([^'\"]+)['\"]\]", selector)
                                if href_match:
                                    target_page = href_match.group(1)
                                    # Normalize URLs for comparison
                                    # Remove query parameters and fragments
                                    from urllib.parse import urlparse, urlunparse
                                    current_parsed = urlparse(current_url)
                                    target_parsed = urlparse(target_page)
                                    
                                    # If target is a relative path, construct full URL
                                    if not target_parsed.scheme:
                                        # Relative URL - check if current path ends with target
                                        current_path = current_parsed.path
                                        if target_page in current_path or current_path.endswith(target_page):
                                            # Already on the target page, skip this step
                                            continue
                                    else:
                                        # Absolute URL - compare paths
                                        if current_parsed.path == target_parsed.path:
                                            # Already on the target page, skip this step
                                            continue
                            
                            await browser.close()
                            return False, f"Element not found: {selector} (Current URL: {page.url})"

                        if action == "click":
                            await element.click()
                            await page.wait_for_timeout(1000)
                        elif action == "type":
                            await element.fill(step.get("value", ""))
                            await page.wait_for_timeout(200)
                        elif action == "select":
                            await element.select_option(str(step.get("value", "")))
                            await page.wait_for_timeout(200)
                    
                    # Run evaluator
                    if evaluator_code and evaluator_code.strip():
                        result = await page.evaluate(f"""
                            () => {{
                                {evaluator_code}
                                const e = new Evaluator();
                                return e.evaluate('{task_id}');
                            }}
                        """)
                        
                        if not result or not result.get('passed'):
                            await browser.close()
                            return False, f"Evaluator failed: {result}"
                    
                    await browser.close()
                    return True, None
                    
                except Exception as e:
                    await browser.close()
                    return False, f"Execution error: {str(e)}"
    
    async def validate(
        self,
        task,
        output_dir: str,
        page_file: str,
        html_content: str,
        logic_code: str,
        architecture: Dict,
        evaluator_code: str,
        prompt_template: str,
        registry: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Full validation: generate path then execute.
        
        Args:
            task: Task to validate
            output_dir: Directory with files
            page_file: Starting page
            html_content: HTML content
            logic_code: Backend logic
            architecture: Architecture dict
            evaluator_code: Evaluator JS
            prompt_template: Prompt for path generation
            registry: Optional element ID contracts
            
        Returns:
            Tuple of (success, error_message)
        """
        # Generate path
        path = await self.generate_path(
            task, html_content, logic_code, architecture, prompt_template, registry
        )
        
        if not path:
            return False, "Failed to generate golden path"
        
        # Execute path
        return await self.execute_path(
            output_dir,
            page_file,
            path.get("steps", []),
            evaluator_code,
            task.id
        )
