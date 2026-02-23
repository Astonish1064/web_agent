import json
from typing import Dict, Any, Optional
from ..interfaces import IControllerGenerator
from ..utils import clean_json_response, with_retry

class LLMControllerGenerator(IControllerGenerator):
    """
    Generates the JavaScript controller layer (`app.js`) to bind static HTML elements to backend logic.
    """
    def __init__(self, llm_provider):
        self.llm = llm_provider
        
    def _parse_js_response(self, response: str) -> str:
        data = clean_json_response(response)
        if not data:
            return ""
        if isinstance(data, dict):
            if "__raw__" in data:
                return data["__raw__"]
            return data.get("app.js", data.get("controller.js", ""))
        return str(data)

    @with_retry(max_retries=3)
    def generate_controller(self, task, html_pages: dict, logic_code: str, spec, registry=None) -> str:
        """
        Generate app.js to bind UI to logic for a specific task.
        """
        interfaces_json = json.dumps([
            {"name": i.name, "parameters": i.parameters, "returns": i.returns, "description": i.description}
            for i in spec.interfaces
        ])
        
        pages_content = ""
        for page_name, html in html_pages.items():
            pages_content += f"\n--- {page_name} ---\n```html\n{html}\n```\n"
        
        prompt = f"""
You are a senior frontend developer. Your EXCLUSIVE task is to write `app.js` (the controller) for the following task.
TASK: {task.description}
STEPS: {json.dumps(task.steps)}

WEBSITE SEED: {spec.seed}
AVAILABLE SDK INTERFACES (provided by logic.js):
{interfaces_json}

STATIC HTML PAGES:
{pages_content}

BACKEND LOGIC IMPLEMENTATION (logic.js):
```javascript
{logic_code}
```
{registry.inject_into_prompt("") if registry else ""}

REQUIREMENTS:
1. Write the JavaScript code for `app.js`. This code will be included in the HTML pages.
2. The HTML pages have already been designed and provided above. DO NOT CHANGE THEM. DO NOT Output HTML.
3. Your job is to select the correct DOM elements using standard `document.getElementById` or `querySelector` and bind event listeners (e.g. `onclick`, `onsubmit`, `DOMContentLoaded`).
4. Read form inputs, call the appropriate `window.WebsiteSDK` method, and update the DOM (e.g., alert on failure, or call `window.location.href` to navigate).
5. If you need to render lists, dynamically create HTML within Javascript and append it to the appropriate container.
6. Make sure to wait for `DOMContentLoaded` before binding events to ensure elements exist.

Return a JSON object with the strict key "app.js" containing your JavaScript code:
{{
  "app.js": "document.addEventListener('DOMContentLoaded', () => {{ ... }});"
}}
"""
        response = self.llm.prompt(prompt)
        return self._parse_js_response(response)

    @with_retry(max_retries=3)
    def fix_controller(self, task, html_pages: dict, current_controller: str, logic_code: str, spec, error: str, registry=None) -> str:
        """
        Fixes app.js based on verification errors.
        """
        interfaces_json = json.dumps([
            {"name": i.name, "parameters": i.parameters, "returns": i.returns, "description": i.description}
            for i in spec.interfaces
        ])
        
        pages_content = ""
        for page_name, html in html_pages.items():
            pages_content += f"\n--- {page_name} ---\n```html\n{html}\n```\n"

        prompt = f"""
You are a senior frontend developer fixing a broken website controller.
The task was: {task.description}

During verification, the following ERROR occurred:
```
{error}
```

CURRENT CONTROLLER (app.js):
```javascript
{current_controller}
```

STATIC HTML PAGES (DO NOT MODIFY THESE, ONLY MODIFY APP.JS):
{pages_content}

BACKEND LOGIC IMPLEMENTATION (logic.js snippet):
```javascript
{logic_code[:1000]} // Truncated to prevent excessive length
```
{registry.inject_into_prompt("") if registry else ""}

REQUIREMENTS:
1. Fix `app.js` to resolve the error. This is usually caused by targeting the wrong DOM IDs, missing an event listener, or incorrect interaction with `window.WebsiteSDK`.
2. DO NOT output HTML. You are ONLY fixing the JavaScript.
3. Keep your existing working code; only fix what's broken based on the error.

Return a JSON object with the strict key "app.js" containing your updated JavaScript code:
{{
  "app.js": "document.addEventListener('DOMContentLoaded', () => {{ ... }});"
}}
"""
        response = self.llm.prompt(prompt)
        return self._parse_js_response(response)
