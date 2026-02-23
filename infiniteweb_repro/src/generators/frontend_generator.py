"""
LLMFrontendGenerator - Phase 4 Implementation

Generates HTML and CSS using official prompts.
"""
import json
from typing import Dict
from ..domain import Framework
from ..interfaces import IFrontendGenerator, ILLMProvider
from ..prompts.library import PROMPT_FRAMEWORK_GENERATION, PROMPT_HTML_GENERATION, PROMPT_CSS_GENERATION
from ..utils import clean_json_response, with_retry



class LLMFrontendGenerator(IFrontendGenerator):
    """Generates frontend assets using LLM."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
    
    @with_retry(max_retries=3)
    def generate_framework(self, spec, arch) -> Framework:
        """Generate shared framework (header/footer)."""
        header_links = json.dumps(getattr(arch, 'header_links', []))
        footer_links = json.dumps(getattr(arch, 'footer_links', []))
        
        prompt = PROMPT_FRAMEWORK_GENERATION.format(
            website_seed=spec.seed,
            header_links_json=header_links,
            footer_links_json=footer_links,
            design_context="{}"  # Optional context
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_framework_response(response)
    
    def _parse_framework_response(self, response: str) -> Framework:
        data = clean_json_response(response)
        if not data:
            return Framework("", "")
        return Framework(
            html=data.get("framework_html", ""),
            css=data.get("framework_css", "")
        )
    
    @with_retry(max_retries=3)
    def generate_html(self, spec, page_spec, page_design, page_arch, framework, logic_code: str) -> str:
        """Generate page HTML."""
        page_design_json = json.dumps(getattr(page_design, '__dict__', {}), default=str)
        page_arch_json = json.dumps(getattr(page_arch, '__dict__', {}), default=str)
        
        data_dict_json = json.dumps([{"name": getattr(m, 'name', '')} for m in spec.data_models])
        # Get full interface definitions for the assigned names
        assigned_names = getattr(page_arch, 'assigned_interfaces', [])
        full_interfaces = [
            {"name": i.name, "parameters": i.parameters, "returns": i.returns, "description": i.description}
            for i in spec.interfaces if i.name in assigned_names
        ]
        page_interfaces = json.dumps(full_interfaces)
        
        prompt = PROMPT_HTML_GENERATION.format(
            website_type=spec.seed,
            page_design_json=page_design_json,
            page_architecture_json=page_arch_json,
            framework_html=framework.html,
            data_dict_json=data_dict_json,
            page_interfaces_json=page_interfaces,
            logic_code=logic_code
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_html_response(response)
        
    def _parse_html_response(self, response: str) -> str:
        data = clean_json_response(response)
        if not data:
            return ""
        # Adaptive Fallback: If clean_json_response found raw code instead of JSON
        if isinstance(data, dict) and "__raw__" in data:
            return data["__raw__"]
        return data.get("html_content", "")
    
    @with_retry(max_retries=3)
    def generate_css(self, page_design, layout, design_analysis, framework, html_content) -> str:
        """Generate page CSS."""
        page_design_json = json.dumps(getattr(page_design, '__dict__', {}), default=str)
        page_layout_json = json.dumps(getattr(layout, '__dict__', {}), default=str)
        design_analysis_json = json.dumps(getattr(design_analysis, '__dict__', {}), default=str)
        
        prompt = PROMPT_CSS_GENERATION.format(
            page_design_json=page_design_json,
            page_layout_json=page_layout_json,
            design_analysis_json=design_analysis_json,
            framework_css=framework.css,
            html_content=html_content[:2000] # Truncate HTML to avoid token limits
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_css_response(response)
        
    def _parse_css_response(self, response: str) -> str:
        data = clean_json_response(response)
        if not data:
            return ""
        # Adaptive Fallback: If clean_json_response found raw code instead of JSON
        if isinstance(data, dict) and "__raw__" in data:
            return data["__raw__"]
        return data.get("css_content", "")

    @with_retry(max_retries=3)
    def implement_task_view(self, task, spec, registry=None) -> Dict[str, str]:
        """
        [INCREMENTAL TCTDD] Generate or update STATIC HTML/CSS for a specific task.
        """
        # Serialize planned pages
        planned_pages_info = "\n".join([
            f"- {p.filename}: {p.description}" 
            for p in getattr(spec, 'pages', [])
        ])
        
        prompt = f"""
You are a senior UI designer. Generate or update ONLY the STATIC HTML pages required to complete this task (NO Javascript logic):
TASK: {task.description}
STEPS: {json.dumps(task.steps)}

WEBSITE SEED: {spec.seed}
{planned_pages_info}
{registry.inject_into_prompt("") if registry else ""}

REQUIREMENTS:
1. Identify which pages from PLANNED PAGES are needed for this task.
2. For each needed page, generate the full STATIC HTML content (including framework and CSS).
3. PROHIBITED: Do NOT write ANY `<script>` tags for logic or event listeners. Do NOT define `mockDB` or functions. ANOTHER agent will handle the JavaScript controller.
4. Ensure the UI includes all necessary elements (buttons, inputs) with unique IDs.
5. You MUST include `<script src="logic.js"></script>` and `<script src="app.js"></script>` in the `<head>` of EVERY HTML page.
6. Ensure navigation links (`href`) between pages works as described in the steps.
7. If the task requires a page not in PLANNED PAGES, you may create it, but prefer adhering to the plan.
8. Render some static mockup elements for things like task lists, until the JavaScript agent takes over.

Return a JSON object where keys are filenames and values are the full HTML content:
{{
  "index.html": "<!DOCTYPE html>...",
  "product.html": "..."
}}
"""
        response = self.llm.prompt(prompt)
        return clean_json_response(response)

    @with_retry(max_retries=3)
    def fix_task_view(self, task, spec, error, current_pages, registry=None) -> Dict[str, str]:
        """
        [INCREMENTAL TCTDD] Fixes the UI based on verification errors (missing elements, etc).
        """
        # We focus on the pages that likely need fixing
        page_context = ""
        for name, html in current_pages.items():
            if name.endswith(".html"):
                page_context += f"--- {name} ---\n{html[:1500]}... (truncated)\n\n"

        prompt = f"""
You are a senior UI designer. The previous HTML implementation for this task FAILED verification.
Please FIX the STATIC HTML to ensure the task can be completed.

TASK: {task.description}
STEPS: {json.dumps(task.steps)}
ERROR REPORT: {error}

WEBSITE SEED: {spec.seed}

{page_context}
{registry.inject_into_prompt("") if registry else ""}

REQUIREMENTS:
1. Analyze the ERROR REPORT carefully.
   - If error is "element not visible" or "Interaction failed", check CSS styles (display:none, visibility:hidden, z-index).
   - If error is "Selector not found", ensure IDs match exactly.
2. Ensure all UI elements required by the TASK STEPS exist and have meaningful IDs or accessible text.
3. Keep the <script src="logic.js"></script> and <script src="app.js"></script> imports.
4. PROHIBITED: Do NOT write ANY `<script>` tags for logic. ANOTHER agent will fix the JavaScript controller.
5. Return the FULL CORRECTED HTML for the affected pages.

Return JSON:
{{
  "category.html": "<!DOCTYPE html>..."
}}
"""
        response = self.llm.prompt(prompt)
        return clean_json_response(response)

    def generate_page(self, spec, page_spec, logic_code) -> str:
        """Legacy compatibility method."""
        return ""
