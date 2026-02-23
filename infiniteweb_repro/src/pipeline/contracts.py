"""
Element ID contracts for consistent selectors.
===============================================
Ensures generators and validators use the same element IDs.
"""
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ElementContract:
    """Defines a standard ID for an interactive element."""
    element_type: str   # "button", "input", "filter", "link"
    action: str         # "add_to_cart", "search", "filter_price"
    page: str           # "index.html", "product.html"
    suggested_id: str   # "#btn-add-to-cart"
    description: str = ""


class SelectorRegistry:
    """
    Central registry for element selectors.
    
    This ensures all generators and validators use consistent IDs.
    Register elements during architecture/interface design,
    then inject the registry into prompts.
    """
    
    # Standard naming conventions by element type
    CONVENTIONS = {
        "button": "btn-{action}",
        "input": "input-{action}",
        "filter": "filter-{action}",
        "form": "form-{action}",
        "link": "link-{action}",
        "select": "select-{action}",
        "card": "card-{action}",
        "container": "container-{action}",
    }
    
    def __init__(self):
        self._registry: Dict[str, ElementContract] = {}
        self._by_page: Dict[str, List[str]] = {}
    
    def register(
        self, 
        element_type: str, 
        action: str, 
        page: str = "global",
        description: str = ""
    ) -> str:
        """
        Generates and registers a standardized selector.
        """
        # Sanitize action: remove quotes, spaces, etc.
        safe_action = action.replace("_", "-").replace(" ", "-").replace("'", "").replace('"', "").lower()
        
        template = self.CONVENTIONS.get(element_type, "{action}")
        selector_id = template.format(action=safe_action)
        full_selector = f"#{selector_id}"
        
        contract = ElementContract(
            element_type=element_type,
            action=action, # Keep original action for keying
            page=page,
            suggested_id=full_selector,
            description=description
        )
        
        key = f"{page}:{action}"
        self._registry[key] = contract
        
        # Track by page
        if page not in self._by_page:
            self._by_page[page] = []
        if full_selector not in self._by_page[page]:
            self._by_page[page].append(full_selector)
        
        return full_selector

    def get(self, action: str, page: str = "global") -> Optional[str]:
        """Gets selector for an action."""
        key = f"{page}:{action}"
        contract = self._registry.get(key)
        return contract.suggested_id if contract else None
    
    def get_page_selectors(self, page: str) -> List[str]:
        """Gets all selectors for a specific page."""
        return self._by_page.get(page, []) + self._by_page.get("global", [])
    
    def to_dict(self) -> Dict[str, str]:
        """Converts registry to action -> selector mapping."""
        return {
            contract.action: contract.suggested_id 
            for contract in self._registry.values()
        }
    
    def to_json(self) -> str:
        """Serializes registry to JSON."""
        return json.dumps(self.to_dict(), indent=2)
    
    def inject_into_prompt(self, prompt: str) -> str:
        """
        Adds selector registry context to a prompt.
        """
        contract_section = f"""

### Element ID Contracts (CRITICAL):
You MUST use these exact IDs for interactive elements to ensure test compatibility.
Choose the ONE most relevant ID from this list for each element you create. 
Do NOT combine multiple IDs into one element.

```json
{self.to_json()}
```

IMPORTANT: In your HTML, use `id="ID_FROM_LIST"`. Do NOT use spaces in IDs.
"""
        return prompt + contract_section
    
    def validate_html(self, html_content: str, page: str) -> List[str]:
        """
        Validates that HTML contains expected selectors.
        """
        missing = []
        expected = self.get_page_selectors(page)
        
        for selector in expected:
            element_id = selector[1:]
            if f'id="{element_id}"' not in html_content and f"id='{element_id}'" not in html_content:
                missing.append(selector)
        
        return missing
    
    @classmethod
    def from_tasks(cls, tasks: List, interfaces: List) -> 'SelectorRegistry':
        """
        Creates a registry from tasks and interfaces using LLM-ready heuristics.
        """
        registry = cls()
        
        # 1. Analyze interfaces first (most explicit)
        for interface in interfaces:
            name = getattr(interface, 'name', '') or ''
            page = getattr(interface, 'page', 'global')
            name_clean = name.lower().replace(' ', '_')
            
            if 'create' in name.lower() or 'add' in name.lower():
                registry.register("button", f"submit_{name_clean}", page=page)
            elif 'search' in name.lower():
                registry.register("input", "search_query", page=page)
                registry.register("button", "search_submit", page=page)
            elif 'list' in name.lower() or 'get' in name.lower():
                registry.register("select", "sort_by", page=page)
                registry.register("button", "filter_open", page=page)

        # 2. Analyze task steps (intent-based)
        for task in tasks:
            steps = getattr(task, 'steps', []) or []
            for step in steps:
                step_lower = step.lower()
                
                # Rule-based heuristics for common actions
                if "filter" in step_lower:
                    registry.register("button", "filter_apply", page="global")
                if "sort" in step_lower:
                    registry.register("select", "sort_by", page="global")
                if "add" in step_lower or "create" in step_lower:
                    registry.register("button", "add_item", page="global")
                if "title" in step_lower or "task" in step_lower:
                    registry.register("input", "task_title", page="global")
                if "due" in step_lower:
                    registry.register("input", "due_date", page="global")
                
        return registry
