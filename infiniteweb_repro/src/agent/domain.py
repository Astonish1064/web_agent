from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from src.domain import Task as GeneratedTask, WebsiteSpec

@dataclass
class Action:
    """Represents an atomic action performed by the Web Agent."""
    type: str  # "click", "type", "scroll", "navigate", "select", "wait", "finish", "fail"
    target: Optional[str] = None  # CSS selector, element text, or description
    value: Optional[str] = None   # Text to type, or value to select
    coordinates: Optional[Tuple[int, int]] = None  # Optional (x, y) for precise clicking
    reasoning: Optional[str] = None  # Agent's internal reasoning for this action

@dataclass
class Observation:
    """Represents the state of the web environment as seen by the Agent."""
    url: str
    page_title: str
    screenshot: Optional[bytes] = None  # PNG binary data
    dom_tree: Optional[str] = None      # Cleaned/Simplified DOM structure
    a11y_tree: Optional[str] = None     # Cleaned A11y tree structure
    visible_text: Optional[str] = None  # Text content visible on the page
    
    # Metadata from InfiniteWeb Architecture/Instrumentation
    instrumentation_state: Dict[str, Any] = field(default_factory=dict)
    current_page_type: Optional[str] = None  # e.g., "index", "product_detail"
    available_pages: List[str] = field(default_factory=list)
    
    # Contextual hints
    last_action_success: bool = True
    last_action_error: Optional[str] = None

@dataclass
class ActionRecord:
    """Detailed record of a single action and its consequences."""
    step: int
    timestamp: float
    action: Action
    observation_before: Observation
    observation_after: Observation
    reward: float
    done: bool
    info: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Trajectory:
    """Complete sequence of actions and observations for a task episode."""
    task: GeneratedTask
    website_dir: str
    actions: List[ActionRecord] = field(default_factory=list)
    total_reward: float = 0.0
    final_success: bool = False
    start_time: float = 0.0
    end_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EpisodeResult:
    """Result of a single task execution by the Agent."""
    success: bool
    steps: int
    total_reward: float
    trajectory: Trajectory
