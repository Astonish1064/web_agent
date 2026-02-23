"""
LLMPageDesigner - Phase 3 Implementation

Designs page functionality, visual analysis, and layout using official prompts.
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict

from ..interfaces import IPageDesigner, ILLMProvider
from ..prompts.library import PROMPT_PAGE_FUNCTIONALITY, PROMPT_DESIGN_ANALYSIS, PROMPT_LAYOUT_DESIGN
from ..utils import clean_json_response, with_retry


@dataclass
class PageFunctionality:
    """Result of page functionality design."""
    core_features: List[str] = field(default_factory=list)
    user_workflows: List[str] = field(default_factory=list)
    interactions: List[str] = field(default_factory=list)
    state_logic: str = ""


@dataclass
class PageDesign:
    """Complete page design output."""
    title: str = ""
    description: str = ""
    page_functionality: Dict = field(default_factory=dict)
    components: List[Dict] = field(default_factory=list)


@dataclass
class DesignAnalysis:
    """Result of design image analysis."""
    visual_features: Dict = field(default_factory=dict)
    color_scheme: Dict = field(default_factory=dict)
    layout_characteristics: Dict = field(default_factory=dict)
    ui_patterns: List[Dict] = field(default_factory=list)
    typography: Dict = field(default_factory=dict)
    spacing_system: Dict = field(default_factory=dict)


@dataclass
class Layout:
    """Layout design result."""
    chosen_strategies: Dict = field(default_factory=dict)
    overall_layout_description: str = ""
    component_layouts: List[Dict] = field(default_factory=list)


class LLMPageDesigner(IPageDesigner):
    """Designs pages using LLM with official prompts."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
    
    @with_retry(max_retries=3)
    def design_functionality(self, page_spec, spec, navigation_info=None) -> PageDesign:
        """Design page functionality and components."""
        page_spec_json = json.dumps({
            "name": getattr(page_spec, 'name', ''),
            "filename": getattr(page_spec, 'filename', '')
        })
        data_dict_json = json.dumps([
            {"name": getattr(m, 'name', '')}
            for m in getattr(spec, 'data_models', [])
        ])
        interface_details = json.dumps([
            {"name": getattr(i, 'name', '')}
            for i in getattr(spec, 'interfaces', [])
        ])
        
        prompt = PROMPT_PAGE_FUNCTIONALITY.format(
            website_seed=spec.seed,
            page_spec_json=page_spec_json,
            data_dict_json=data_dict_json,
            interface_details_json=interface_details,
            navigation_info=json.dumps(navigation_info) if navigation_info else "{}"
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_functionality_response(response)
    
    def _parse_functionality_response(self, response: str) -> PageDesign:
        """Parse functionality response."""
        data = clean_json_response(response)
        if not data:
            return PageDesign(title="Untitled")
            
        return PageDesign(
            title=data.get("title", "Untitled"),
            description=data.get("description", ""),
            page_functionality=data.get("page_functionality", {}),
            components=data.get("components", [])
        )
    
    @with_retry(max_retries=3)
    def analyze_design(self, seed: str) -> DesignAnalysis:
        """Analyze design to extract visual characteristics."""
        prompt = PROMPT_DESIGN_ANALYSIS.format(website_seed=seed)
        
        response = self.llm.prompt(prompt)
        return self._parse_design_response(response)
    
    def _parse_design_response(self, response: str) -> DesignAnalysis:
        """Parse design analysis response."""
        data = clean_json_response(response)
        if not data:
            return DesignAnalysis()
            
        return DesignAnalysis(
            visual_features=data.get("visual_features", {}),
            color_scheme=data.get("color_scheme", {}),
            layout_characteristics=data.get("layout_characteristics", {}),
            ui_patterns=data.get("ui_patterns", []),
            typography=data.get("typography", {}),
            spacing_system=data.get("spacing_system", {})
        )
    
    @with_retry(max_retries=3)
    def design_layout(self, page_spec, design_analysis, components: list, seed: str) -> Layout:
        """Design layout for page components."""
        visual_style = getattr(design_analysis, 'visual_features', {}).get('overall_style', 'modern')
        grid_system = getattr(design_analysis, 'layout_characteristics', {}).get('grid_system', '12-column')
        spacing = getattr(design_analysis, 'spacing_system', {})
        
        prompt = PROMPT_LAYOUT_DESIGN.format(
            visual_style=visual_style,
            grid_system=grid_system,
            layout_pattern="standard",
            spacing_system_json=json.dumps(spacing),
            website_seed=seed,
            page_name=getattr(page_spec, 'name', 'Page'),
            components_list=json.dumps(components)
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_layout_response(response)
    
    def _parse_layout_response(self, response: str) -> Layout:
        """Parse layout response."""
        data = clean_json_response(response)
        if not data:
            return Layout()
            
        return Layout(
            chosen_strategies=data.get("chosen_strategies", {}),
            overall_layout_description=data.get("overall_layout_description", ""),
            component_layouts=data.get("component_layouts", [])
        )
