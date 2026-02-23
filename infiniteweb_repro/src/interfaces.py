from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .domain import WebsiteSpec, GenerationContext, InstrumentationSpec, PageSpec

# Forward imports for runtime
from .domain import WebsiteSpec, GenerationContext, InstrumentationSpec, PageSpec


# =============================================================================
# Phase 1: Planning Interfaces
# =============================================================================

class ITaskGenerator(ABC):
    """Generates user tasks from a website seed."""
    
    @abstractmethod
    def generate(self, seed: str, config) -> List:
        """
        Generate tasks based on seed and configuration.
        
        Args:
            seed: Website type/seed (e.g., "online_bookstore")
            config: TaskConfig with generation parameters
            
        Returns:
            List of GeneratedTask objects
        """
        pass


class IInterfaceDesigner(ABC):
    """Designs API interfaces based on tasks and pages."""
    
    @abstractmethod
    def design(self, spec) -> List:
        """
        Design interfaces for the website.
        
        Args:
            spec: WebsiteSpec with tasks, data_models, pages
            
        Returns:
            List of InterfaceDef objects
        """
        pass
    
    @abstractmethod
    def wrap(self, interfaces: List, data_models: List):
        """
        Wrap interfaces to hide system-managed parameters.
        
        Args:
            interfaces: Original interfaces
            data_models: Existing data models
            
        Returns:
            WrappedInterfaces with state models and mappings
        """
        pass


class IArchitectDesigner(ABC):
    """Designs website architecture with page structure and navigation."""
    
    @abstractmethod
    def design(self, spec):
        """
        Design website architecture.
        
        Args:
            spec: WebsiteSpec with tasks, interfaces, data_models
            
        Returns:
            Architecture with pages, navigation, header links
        """
        pass


class ISpecGenerator(ABC):
    @abstractmethod
    def generate(self, seed: str) -> WebsiteSpec:
        """
        Generates the unified specification (tasks, interfaces, models) from a seed.
        """
        pass


class IDataGenerator(ABC):
    """Generates realistic website data based on data models."""
    
    @abstractmethod
    def generate(self, spec) -> dict:
        """
        Generate static data for the website.
        
        Args:
            spec: WebsiteSpec with data_models and tasks
            
        Returns:
            dict with data collections (e.g., products, categories)
        """
        pass


class IInstrumentationGenerator(ABC):
    @abstractmethod
    def generate_spec(self, spec: WebsiteSpec) -> InstrumentationSpec:
        """
        Analyzes the tasks and specs to determine where instrumentation is needed.
        """
        pass

class IBackendGenerator(ABC):
    @abstractmethod
    def generate_logic(self, spec: WebsiteSpec, instr_spec: InstrumentationSpec) -> str:
        """
        Generates the business logic (logic.js) using TCTDD (conceptually).
        Injects instrumentation based on instr_spec.
        Returns the JavaScript code as a string.
        """
        pass


class IPageDesigner(ABC):
    """Designs page functionality, layout, and visual analysis."""
    
    @abstractmethod
    def design_functionality(self, page_spec, spec):
        """Design page functionality and components."""
        pass
    
    @abstractmethod
    def analyze_design(self, seed: str):
        """Analyze design to extract visual characteristics."""
        pass
    
    @abstractmethod
    def design_layout(self, page_spec, design_analysis, components: list, seed: str):
        """Design layout for page components."""
        pass


class IFrontendGenerator(ABC):
    """Generates frontend assets (HTML, CSS)."""
    
    @abstractmethod
    def generate_framework(self, spec, arch):
        """Generate shared framework (header/footer)."""
        pass
        
    @abstractmethod
    def generate_html(self, spec, page_spec, page_design, page_arch, framework, logic_code: str) -> str:
        """Generate page HTML."""
        pass
        
    @abstractmethod
    def generate_css(self, page_design, layout, design_analysis, framework, html_content) -> str:
        """Generate page CSS."""
        pass

    @abstractmethod
    def generate_page(self, spec: WebsiteSpec, page_spec: PageSpec, logic_code: str) -> str:
        """Legacy compatibility method."""
        pass

    @abstractmethod
    def implement_task_view(self, task, spec, registry=None) -> dict:
        """[INCREMENTAL TCTDD] Generate or update HTML/CSS for a specific task."""
        pass

    @abstractmethod
    def fix_task_view(self, task, spec, error, current_pages, registry=None) -> dict:
        """[INCREMENTAL TCTDD] Fixes the UI based on verification errors."""
        pass

class IControllerGenerator(ABC):
    @abstractmethod
    def generate_controller(self, task, html_pages: dict, logic_code: str, spec, registry=None) -> str:
        """[INCREMENTAL TCTDD] Generate app.js to bind UI to logic for a specific task."""
        pass

    @abstractmethod
    def fix_controller(self, task, html_pages: dict, current_controller: str, logic_code: str, spec, error, registry=None) -> str:
        """[INCREMENTAL TCTDD] Fixes app.js based on Agent verification errors/trajectories."""
        pass

class IInstrumentationGenerator(ABC):
    @abstractmethod
    def analyze(self, spec: WebsiteSpec, logic_code: str):
        """Analyze logic to determine instrumentation needs."""
        pass
        
    @abstractmethod
    def inject(self, logic_code: str, instr_spec) -> str:
        """Inject instrumentation code."""
        pass
        
    @abstractmethod
    def generate_spec(self, spec: WebsiteSpec) -> InstrumentationSpec:
        """Legacy compatibility."""
        pass


class IEvaluatorGenerator(ABC):
    @abstractmethod
    def generate(self, spec: WebsiteSpec, instr_spec, logic_code: str) -> str:
        """Generate evaluator script."""
        pass

class ILLMProvider(ABC):
    """Abstract interface for LLM interactions."""
    @abstractmethod
    def prompt(self, prompt_text: str, system_prompt: str = "") -> str:
        pass

    @abstractmethod
    def prompt_json(self, prompt_text: str, system_prompt: str = "") -> dict:
        pass
