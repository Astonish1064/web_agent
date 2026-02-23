import asyncio
import os
import logging
from typing import List, Tuple, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from ..interfaces import IAgentEnvironment, ISnapshotable
from ..domain import Action, Observation
from .action_executor import ActionExecutor
from .server import LocalWebServer
from .a11y_processor import A11yProcessor
from ..evaluation.web_evaluator import WebEvaluator
from src.domain import Task

logger = logging.getLogger("agent.env")

class PlaywrightEnvironment(IAgentEnvironment, ISnapshotable):
    """Playwright-based implementation of the Web Agent Environment."""
    
    def __init__(self, headless: bool = True, viewport: Dict[str, int] = {"width": 1280, "height": 720}):
        self.headless = headless
        self.viewport = viewport
        self.pw = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.server: Optional[LocalWebServer] = None
        self.evaluator: Optional[WebEvaluator] = None
        self.a11y_processor = A11yProcessor()
        self.executor = ActionExecutor()
        self._current_task: Optional[Task] = None
        self._obs: Optional[Observation] = None

    async def start(self):
        """Initializes the Playwright browser."""
        if self.pw:
            return
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(viewport=self.viewport)
        self.page = await self.context.new_page()
        # Debugging: Log console output
        self.page.on("console", lambda msg: print(f"console: {msg.text}"))
        self.page.on("pageerror", lambda err: print(f"pageerror: {err}"))

    async def stop(self):
        """Clean up resources."""
        if self.server:
            self.server.stop()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()
        self.pw = None

    async def reset(self, website_dir: str, task: Task) -> Observation:
        """Resets the environment for a new task."""
        if not self.pw:
            await self.start()
            
        self._current_task = task
        
        # 1. Start/Restart Local Server
        if self.server:
            self.server.stop()
        self.server = LocalWebServer(website_dir)
        self.evaluator = WebEvaluator(website_dir)
        self.server.start()
        
        # 2. Navigate to homepage
        await self.page.goto(self.server.url, wait_until="networkidle")
        
        # 3. Get initial observation
        self._obs = await self._capture_observation()
        return self._obs

    async def step(self, action: Action) -> Tuple[Observation, float, bool, dict]:
        """Executes one action and returning (obs, reward, done, info)."""
        if not self.page:
            raise RuntimeError("Environment not initialized. Call reset() first.")
            
        # 1. Execute Action
        success = await self.executor.execute(self.page, action)
        
        # 2. Wait for stabilization
        await self.page.wait_for_load_state("networkidle", timeout=5000)
        await asyncio.sleep(0.5) # Extra buffer
        
        # 3. Capture new observation
        self._obs = await self._capture_observation()
        self._obs.last_action_success = success
        
        # 4. Check status from evaluator.js
        reward = 0.0
        if self.evaluator and self._current_task:
            reward = await self.evaluator.evaluate_task(self.page, self._current_task.id)
            
        done = action.type in ["finish", "fail"] or reward >= 1.0
        info = {"success": success, "reward": reward}
        
        return self._obs, reward, done, info

    async def _capture_observation(self) -> Observation:
        """Captures screenshot, DOM, and other metadata."""
        screenshot = await self.page.screenshot(type="png")
        dom_tree = await self.page.content() # Simplified DOM logic will go here
        
        # Capture A11y tree via CDP
        try:
            # 1. Inject IDs directly into AX properties (aria-label) so they survive the CDP trip
            await self.page.evaluate("""() => {
                window.__agent_ids__ = {}; // Store original labels to revert later if needed
                
                let idCounter = 1;
                document.querySelectorAll('*').forEach(el => {
                    // Check interactivity
                    const style = window.getComputedStyle(el);
                    const tag = el.tagName.toLowerCase();
                    const isInteractive = 
                        ['button', 'a', 'input', 'select', 'textarea'].includes(tag) ||
                        el.hasAttribute('onclick') || 
                        el.onclick ||
                        style.cursor === 'pointer' ||
                        ['button', 'link', 'textbox', 'checkbox', 'radio'].includes(el.getAttribute('role'));
                        
                    if (isInteractive) {
                        const aid = idCounter++;
                        
                        // Priority for name: aria-label > placeholder > innerText > alt > title
                        let originalLabel = 
                            el.getAttribute('aria-label') || 
                            el.getAttribute('placeholder') || 
                            el.innerText || 
                            el.getAttribute('alt') || 
                            el.getAttribute('title') || 
                            '';
                        
                        // Clean up newlines and extra spaces
                        originalLabel = originalLabel.replace(/\s+/g, ' ').trim();
                        
                        el.setAttribute('aria-label', `${originalLabel} --agent-id:${aid}--`);
                        el.setAttribute('data-agent-id', aid.toString());
                    }
                });
            }""")

            # 2. Capture AXTree (now enriched with IDs)
            client = await self.page.context.new_cdp_session(self.page)
            await client.send("Accessibility.enable")
            cdp_snapshot = await client.send("Accessibility.getFullAXTree")
            
            # 3. Process
            a11y_tree = self.a11y_processor.process(cdp_snapshot)
            
            # 4. Cleanup (Optional, removed to save time/tokens, and it might help visual debugging)
            # await self.page.evaluate("...")
            
        except Exception as e:
            logger.warning(f"Failed to capture A11y tree via CDP: {e}")
            a11y_tree = "Error: Could not capture A11y tree."
        except Exception as e:
            logger.warning(f"Failed to capture A11y tree via CDP: {e}")
            a11y_tree = "Error: Could not capture A11y tree."
        
        # Try to read instrumentation variables
        instrumentation = await self.page.evaluate("window.__instrumentation || {}")
        
        return Observation(
            url=self.page.url,
            page_title=await self.page.title(),
            screenshot=screenshot,
            dom_tree=dom_tree,
            a11y_tree=a11y_tree,
            instrumentation_state=instrumentation,
            available_pages=[] # To be populated from Architecture
        )

    def get_observation(self) -> Observation:
        return self._obs

    # ISnapshotable implementation
    async def save_snapshot(self) -> Any:
        # Save cookies and storage
        cookies = await self.context.cookies()
        local_storage = await self.page.evaluate("JSON.stringify(localStorage)")
        return {
            "url": self.page.url,
            "cookies": cookies,
            "local_storage": local_storage
        }

    async def restore_snapshot(self, snapshot: Any) -> bool:
        try:
            await self.context.add_cookies(snapshot["cookies"])
            await self.page.goto(snapshot["url"])
            if snapshot["local_storage"]:
                await self.page.evaluate("""state => { 
                const data = JSON.parse(state);
                for (let key in data) localStorage.setItem(key, data[key]);
            }""", snapshot["local_storage"])
            return True
        except Exception:
            return False
