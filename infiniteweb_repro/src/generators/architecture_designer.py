"""
LLMArchitectDesigner - Phase 1.3 Implementation

Designs website architecture using PROMPT_ARCHITECTURE_DESIGN.
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict

from ..interfaces import IArchitectDesigner, ILLMProvider
from ..prompts.library import PROMPT_ARCHITECTURE_DESIGN
from ..utils import clean_json_response


@dataclass
class PageArchitecture:
    """Page with navigation and interface assignments."""
    name: str
    filename: str
    assigned_interfaces: List[str] = field(default_factory=list)
    incoming_params: List[str] = field(default_factory=list)
    outgoing_connections: List[Dict] = field(default_factory=list)
    access_methods: List[Dict] = field(default_factory=list)

    @staticmethod
    def from_dict(d):
        return PageArchitecture(**d)

    def to_dict(self):
        return {
            "name": self.name,
            "filename": self.filename,
            "assigned_interfaces": self.assigned_interfaces,
            "incoming_params": self.incoming_params,
            "outgoing_connections": self.outgoing_connections,
            "access_methods": self.access_methods
        }


@dataclass
class Architecture:
    """Complete website architecture."""
    all_pages: List[Dict] = field(default_factory=list)
    pages: List[PageArchitecture] = field(default_factory=list)
    header_links: List[Dict] = field(default_factory=list)
    footer_links: List[Dict] = field(default_factory=list)

    @staticmethod
    def from_dict(d):
        return Architecture(
            all_pages=d.get('all_pages', []),
            pages=[PageArchitecture.from_dict(p) for p in d.get('pages', [])],
            header_links=d.get('header_links', []),
            footer_links=d.get('footer_links', [])
        )
    
    def to_dict(self):
        return {
            "all_pages": self.all_pages,
            "pages": [p.to_dict() for p in self.pages],
            "header_links": self.header_links,
            "footer_links": self.footer_links
        }


class LLMArchitectDesigner(IArchitectDesigner):
    """Designs website architecture using LLM."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
    
    def design(self, spec) -> Architecture:
        """Design website architecture from spec."""
        # Prepare inputs
        task_summary = json.dumps([
            {"id": getattr(t, 'id', ''), "description": getattr(t, 'description', '')}
            for t in getattr(spec, 'tasks', [])
        ])
        interface_summary = json.dumps([
            {"name": getattr(i, 'name', '')}
            for i in getattr(spec, 'interfaces', [])
        ])
        data_summary = json.dumps([
            {"name": getattr(m, 'name', '')}
            for m in getattr(spec, 'data_models', [])
        ])
        
        # Initial architecture (if pages exist, use them)
        pages = getattr(spec, 'pages', [])
        primary_arch = json.dumps([
            {"name": getattr(p, 'name', ''), "filename": getattr(p, 'filename', '')}
            for p in pages
        ]) if pages else "[]"
        
        prompt = PROMPT_ARCHITECTURE_DESIGN.format(
            website_seed=spec.seed,
            task_summary_json=task_summary,
            primary_arch_json=primary_arch,
            interface_summary_json=interface_summary,
            data_summary_json=data_summary
        )
        
        response = self.llm.prompt(prompt)
        return self._parse_response(response)
    
    def _parse_response(self, response: str) -> Architecture:
        """Parse LLM response into Architecture."""
        data = clean_json_response(response)
        if not data:
            return Architecture()
        
        pages = []
        for page_data in data.get("pages", []):
            pages.append(PageArchitecture(
                name=page_data.get("name", "Unnamed"),
                filename=page_data.get("filename", "page.html"),
                assigned_interfaces=page_data.get("assigned_interfaces", []),
                incoming_params=page_data.get("incoming_params", []),
                outgoing_connections=page_data.get("outgoing_connections", []),
                access_methods=page_data.get("access_methods", [])
            ))
        
        return Architecture(
            all_pages=data.get("all_pages", []),
            pages=pages,
            header_links=data.get("header_links", []),
            footer_links=data.get("footer_links", [])
        )
