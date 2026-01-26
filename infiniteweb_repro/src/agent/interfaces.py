from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional
from .domain import Action, Observation, EpisodeResult, Trajectory
from src.domain import Task

class IAgentEnvironment(ABC):
    """Interface for the Web Interaction Environment."""
    
    @abstractmethod
    async def reset(self, website_dir: str, task: Task) -> Observation:
        """Resets the environment and loads a specific task-website pair."""
        pass
    
    @abstractmethod
    async def step(self, action: Action) -> Tuple[Observation, float, bool, dict]:
        """Executes an action and returns the new state."""
        pass
    
    @abstractmethod
    def get_observation(self) -> Observation:
        """Current snapshot of the environment."""
        pass

class ISnapshotable(ABC):
    """Interface for environments that support state snapshots and rollbacks."""
    
    @abstractmethod
    async def save_snapshot(self) -> Any:
        """Saves current environment state (cookies, storage, etc.)."""
        pass
    
    @abstractmethod
    async def restore_snapshot(self, snapshot: Any) -> bool:
        """Restores environment to a previously saved state."""
        pass

class IWebAgent(ABC):
    """Interface for the Web Agent decision maker."""
    
    @abstractmethod
    async def decide(self, observation: Observation, task: Task, history: List[Action]) -> Action:
        """Given current state and history, decide next action."""
        pass
    
    @abstractmethod
    def reset(self):
        """Reset agent's internal state (memory, etc.)."""
        pass

class ITrajectoryRecorder(ABC):
    """Interface for monitoring and recording agent actions."""
    
    @abstractmethod
    def start(self, task: Task, website_dir: str):
        """Starts recording for a new episode."""
        pass
    
    @abstractmethod
    def record(self, action: Action, obs_before: Observation, obs_after: Observation, reward: float, done: bool, info: dict):
        """Records a single step."""
        pass
    
    @abstractmethod
    def finalize(self, success: bool, total_reward: float) -> Trajectory:
        """Completes the recording and returns the final trajectory."""
        pass
