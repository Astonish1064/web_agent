import gymnasium as gym
from gymnasium import spaces
import numpy as np
import asyncio
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import io

from ..domain import Action, Observation
from .playwright_env import PlaywrightEnvironment
from src.domain import Task

class WebGymEnv(gym.Env):
    """
    Gymnasium wrapper for the Playwright Web Environment.
    Bridges the async Playwright logic to a standard Gym interface.
    """
    metadata = {"render_modes": ["rgb_array"]}

    def __init__(self, headless: bool = True):
        super().__init__()
        self.pw_env = PlaywrightEnvironment(headless=headless)
        self.loop = asyncio.get_event_loop()
        
        # Observation space: Screenshot (RGB)
        # We can expand this to include DOM/URL in a Dict space
        self.observation_space = spaces.Dict({
            "screenshot": spaces.Box(low=0, high=255, shape=(720, 1280, 3), dtype=np.uint8),
            "url": spaces.Text(max_length=1024),
            "dom": spaces.Text(max_length=100000)
        })
        
        # Action space: We'll use a simplified Discrete/Box combo or Custom space
        # For LLM Agents, they often use Text as action, but for RL we need structure.
        # Here we provide a flexible structure.
        self.action_space = spaces.Dict({
            "type": spaces.Discrete(8), # click, type, scroll_up, scroll_down, navigate, select, finish, fail
            "x": spaces.Box(low=0, high=1280, shape=(1,)),
            "y": spaces.Box(low=0, high=720, shape=(1,)),
            "text": spaces.Text(max_length=256)
        })

    def reset(self, seed=None, options=None):
        """Standard Gym reset."""
        super().reset(seed=seed)
        
        if not options or "website_dir" not in options or "task" not in options:
            raise ValueError("reset() requires 'website_dir' and 'task' in options.")
            
        website_dir = options["website_dir"]
        task = options["task"]
        
        # Run the async reset
        obs = self.loop.run_until_complete(self.pw_env.reset(website_dir, task))
        
        gym_obs = self._to_gym_obs(obs)
        info = {"url": obs.url}
        return gym_obs, info

    def step(self, action_dict: Dict[str, Any]):
        """Standard Gym step."""
        # Convert gym action back to domain.Action
        action_map = {
            0: "click", 1: "type", 2: "scroll", 3: "scroll", 
            4: "navigate", 5: "select", 6: "finish", 7: "fail"
        }
        
        # Simplified mapping logic
        a_type = action_map[action_dict["type"]]
        action = Action(
            type=a_type,
            coordinates=(int(action_dict["x"][0]), int(action_dict["y"][0])) if "x" in action_dict else None,
            value=action_dict.get("text")
        )
        
        # Run the async step
        obs, reward, done, info = self.loop.run_until_complete(self.pw_env.step(action))
        
        truncated = False
        return self._to_gym_obs(obs), reward, done, truncated, info

    def _to_gym_obs(self, obs: Observation) -> Dict[str, Any]:
        """Converts domain Observation to Gym-compatible Dict."""
        # Process screenshot
        img = Image.open(io.BytesIO(obs.screenshot))
        img_array = np.array(img.convert("RGB"))
        
        return {
            "screenshot": img_array,
            "url": obs.url,
            "dom": obs.dom_tree or ""
        }

    def close(self):
        self.loop.run_until_complete(self.pw_env.stop())
        super().close()
