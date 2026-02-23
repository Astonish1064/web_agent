import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import Page, ElementHandle
from ..domain import Action

logger = logging.getLogger("agent.executor")

class ActionExecutor:
    """Executes atomic Agent actions on a Playwright Page."""
    
    async def execute(self, page: Page, action: Action) -> bool:
        """Executes the given action on the page."""
        try:
            method_name = f"_execute_{action.type.lower()}"
            executor = getattr(self, method_name, None)
            
            if not executor:
                logger.error(f"Unsupported action type: {action.type}")
                return False
                
            logger.info(f"Executing {action.type} on {action.target or 'current context'}")
            return await executor(page, action)
            
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            return False

    async def _execute_click(self, page: Page, action: Action) -> bool:
        if action.coordinates:
            x, y = action.coordinates
            await page.mouse.click(x, y)
        elif action.target:
            locator = self._get_locator(page, action.target)
            if locator:
                await locator.first.click(timeout=5000)
                return True
            
            # Fallback to CSS only if not semantic
            if not action.target.startswith("["):
                await page.click(action.target, timeout=5000)
                return True
            return False
        else:
            return False

    async def _execute_type(self, page: Page, action: Action) -> bool:
        if not action.target or action.value is None:
            return False
        locator = self._get_locator(page, action.target)
        if locator:
            await locator.first.fill(str(action.value), timeout=5000)
            return True
            
        # Fallback to CSS only if not semantic
        if not action.target.startswith("["):
            await page.fill(action.target, str(action.value), timeout=5000)
            return True
        return False

    def _get_locator(self, page: Page, target: str):
        """Attempts to resolve a target (Semantic or ID) to a Playwright Locator."""
        # Strategy 0: Check for Agent ID (Integers)
        if str(target).isdigit():
             return page.locator(f'[data-agent-id="{target}"]')

        import re
        # Pattern: [role] 'name'
        match = re.match(r"\[(\w+)\]\s*'([^']*)'", target)
        if match:
            role, name = match.groups()
            # Map common aliases to Playwright roles
            role_map = {
                "button": "button",
                "link": "link",
                "textbox": "textbox",
                "checkbox": "checkbox",
                "combobox": "combobox",
                "heading": "heading",
                "list": "list",
                "listitem": "listitem",
                "date": "textbox",
                "spinbutton": "spinbutton"
            }
            pw_role = role_map.get(role.lower(), role.lower())
            
            # Strategy 1: Try get_by_role
            try:
                locator = page.get_by_role(pw_role, name=name)
                # Check if it exists (roughly)
                return locator
            except:
                pass
                
            # Strategy 2: Try get_by_label (often better for inputs with internal parts)
            try:
                return page.get_by_label(name, exact=False)
            except:
                pass
        return None

    async def _execute_scroll(self, page: Page, action: Action) -> bool:
        # Simple scroll down if no value, or scroll by amount
        if action.value:
            await page.evaluate(f"window.scrollBy(0, {action.value})")
        else:
            await page.evaluate("window.scrollBy(0, 500)")
        return True

    async def _execute_navigate(self, page: Page, action: Action) -> bool:
        if not action.value:
            return False
        await page.goto(action.value, wait_until="networkidle", timeout=10000)
        return True

    async def _execute_select(self, page: Page, action: Action) -> bool:
        if not action.target or not action.value:
            return False
            
        locator = self._get_locator(page, action.target)
        if locator:
            # Use the locator to select the option
            await locator.select_option(label=action.value, timeout=5000)
        else:
            # Fallback to CSS selector
            await page.select_option(action.target, label=action.value, timeout=5000)
        return True

    async def _execute_wait(self, page: Page, action: Action) -> bool:
        timeout = 2000 # default 2s
        if action.value:
            try:
                timeout = int(action.value)
            except:
                pass
        await asyncio.sleep(timeout / 1000)
        return True

    async def _execute_finish(self, page: Page, action: Action) -> bool:
        # Mark as done (handled by env loop)
        return True

    async def _execute_fail(self, page: Page, action: Action) -> bool:
        # Mark as failed (handled by env loop)
        return True
