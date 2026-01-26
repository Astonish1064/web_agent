import json
import os
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from ..domain import Action, Observation, ActionRecord, Trajectory
from src.domain import Task

logger = logging.getLogger("agent.monitoring")

class TrajectoryRecorder:
    """Records Agent episodes into JSONL and associated PNG files."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.current_trajectory: Optional[Trajectory] = None
        self.step_count = 0
        
    def start(self, task: Task, website_dir: str):
        """Initializes a new recording session."""
        self.step_count = 0
        self.current_trajectory = Trajectory(
            task=task,
            website_dir=website_dir,
            start_time=time.time()
        )
        # Create directory for screenshots
        self.traj_dir = os.path.join(self.output_dir, f"traj_{task.id}_{int(self.current_trajectory.start_time)}")
        os.makedirs(self.traj_dir, exist_ok=True)
        
        logger.info(f"Started recording trajectory for task {task.id} in {self.traj_dir}")

    def record(self, action: Action, obs_before: Observation, obs_after: Observation, 
               reward: float, done: bool, info: dict):
        """Records a single step to JSONL and saves screenshot."""
        self.step_count += 1
        timestamp = time.time()
        time_str = datetime.fromtimestamp(timestamp).strftime("%Y%m%d@%H%M%S%f")
        
        # Save screenshot
        screenshot_filename = f"step_{self.step_count}_{time_str}.png"
        screenshot_path = os.path.join(self.traj_dir, screenshot_filename)
        if obs_after.screenshot:
            with open(screenshot_path, "wb") as f:
                f.write(obs_after.screenshot)

        # Create record
        record = ActionRecord(
            step=self.step_count,
            timestamp=timestamp,
            action=action,
            observation_before=obs_before,
            observation_after=obs_after,
            reward=reward,
            done=done,
            info=info
        )
        self.current_trajectory.actions.append(record)
        
        # Write to JSONL
        jsonl_path = os.path.join(self.traj_dir, "traj.jsonl")
        log_entry = {
            "step_num": self.step_count,
            "action_timestamp": time_str,
            "action": self._action_to_dict(action),
            "reward": reward,
            "done": done,
            "screenshot_file": screenshot_filename,
            "url": obs_after.url,
            "instrumentation": obs_after.instrumentation_state,
            "info": info
        }
        
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def finalize(self, success: bool, total_reward: float) -> Trajectory:
        """Completes the recording."""
        if not self.current_trajectory:
            return None
            
        self.current_trajectory.end_time = time.time()
        self.current_trajectory.final_success = success
        self.current_trajectory.total_reward = total_reward
        
        # Save final summary
        summary_path = os.path.join(self.traj_dir, "summary.json")
        summary = {
            "task_id": self.current_trajectory.task.id,
            "success": success,
            "total_reward": total_reward,
            "steps": self.step_count,
            "duration": self.current_trajectory.end_time - self.current_trajectory.start_time
        }
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"Finalized trajectory in {self.traj_dir}. Success: {success}")
        return self.current_trajectory

    def _action_to_dict(self, action: Action) -> Dict[str, Any]:
        return {
            "type": action.type,
            "target": action.target,
            "value": action.value,
            "coordinates": action.coordinates,
            "reasoning": action.reasoning
        }
