"""
LLMFrontendGenerator - Phase 4 Implementation

Generates HTML and CSS using official prompts.
"""
import json
from dataclasses import dataclass

from ..interfaces import IFrontendGenerator, ILLMProvider
from ..prompts.library import PROMPT_FRAMEWORK_GENERATION, PROMPT_HTML_GENERATION, PROMPT_CSS_GENERATION
from ..utils import clean_json_response


@dataclass
class Framework:
    """Shared UI framework."""
    html: str
    css: str


class LLMFrontendGenerator(IFrontendGenerator):
    """Generates frontend assets using LLM."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
    
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
    
    def generate_html(self, spec, page_spec, page_design, page_arch, framework) -> str:
        """Generate page HTML."""
        page_design_json = json.dumps(getattr(page_design, '__dict__', {}), default=str)
        page_arch_json = json.dumps(getattr(page_arch, '__dict__', {}), default=str)
        
        data_dict_json = json.dumps([{"name": getattr(m, 'name', '')} for m in spec.data_models])
        page_interfaces = json.dumps(getattr(page_arch, 'assigned_interfaces', []))
        
        prompt = PROMPT_HTML_GENERATION.format(
            website_type=spec.seed,
            page_design_json=page_design_json,
            page_architecture_json=page_arch_json,
            framework_html=framework.html,
            data_dict_json=data_dict_json,
            page_interfaces_json=page_interfaces
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_html_response(response)
        
    def _parse_html_response(self, response: str) -> str:
        data = clean_json_response(response)
        if not data:
            return ""
        return data.get("html_content", "")
    
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
        return data.get("css_content", "")

    def generate_page(self, spec, page_spec, logic_code) -> str:
        """Legacy compatibility method."""
        return ""
