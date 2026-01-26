import asyncio
import os
import logging
from typing import List, Dict, Any
from .interfaces import IWebAgent, IAgentEnvironment
from .monitoring.trajectory_recorder import TrajectoryRecorder
from .domain import EpisodeResult, Trajectory
from src.domain import Task, GenerationContext

logger = logging.getLogger("agent.runner")

class AgentRunner:
    """Orchestrates the execution of Web Agent episodes on generated websites."""
    
    def __init__(self, env: IAgentEnvironment, agent: IWebAgent, output_dir: str):
        self.env = env
        self.agent = agent
        self.output_dir = output_dir
        self.recorder = TrajectoryRecorder(output_dir)

    async def run_task(self, website_dir: str, task: Task, max_steps: int = 15) -> EpisodeResult:
        """Runs the Agent on a specific task."""
        logger.info(f"🚀 Running task: {task.id}")
        
        # 1. Start recording
        self.recorder.start(task, website_dir)
        
        # 2. Reset environment
        obs = await self.env.reset(website_dir, task)
        self.agent.reset()
        
        history = []
        total_reward = 0
        success = False
        
        # 3. Execution Loop
        for step in range(1, max_steps + 1):
            # Agent decides
            action = await self.agent.decide(obs, task, history)
            
            # Record before state (for reference)
            obs_before = obs
            
            # Environment steps
            obs, reward, done, info = await self.env.step(action)
            
            # Record transition
            self.recorder.record(action, obs_before, obs, reward, done, info)
            
            history.append(action)
            total_reward += reward
            
            logger.info(f"Step {step}: {action.type}({action.target or ''}) -> Success: {info.get('success', True)}")
            
            if done:
                if action.type == "finish":
                    success = True
                break
        
        # 4. Finalize
        traj = self.recorder.finalize(success, total_reward)
        return EpisodeResult(
            success=success,
            steps=len(history),
            total_reward=total_reward,
            trajectory=traj
        )

    async def run_all_tasks(self, context: GenerationContext) -> List[EpisodeResult]:
        """Runs the Agent on all tasks generated in the context."""
        results = []
        for task in context.spec.tasks:
            result = await self.run_task(context.output_dir, task)
            results.append(result)
        return results
