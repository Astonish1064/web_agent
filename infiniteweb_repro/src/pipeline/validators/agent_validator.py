import os
import asyncio
import logging
from typing import Tuple, Optional, Dict
from src.agent.environments.playwright_env import PlaywrightEnvironment
from src.agent.agents.llm_agent import LLMWebAgent
from src.agent.runner import AgentRunner
from src.domain import Task

logger = logging.getLogger("pipeline.agent_validator")

class AgentValidator:
    """
    Validates a task using an autonomous LLM Web Agent instead of a rigid Golden Path.
    """
    def __init__(self, llm_provider, config):
        self.llm = llm_provider
        self.config = config

    async def validate(
        self,
        task: Task,
        output_dir: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Runs the autonomous agent to verify the task.
        
        Args:
            task: Task to validate
            output_dir: Directory where the generated website lives
            
        Returns:
            Tuple of (success, error_message). If failed, error_message contains the trajectory.
        """
        env = None
        try:
            # Initialize environment in headless mode
            env = PlaywrightEnvironment(headless=True)
            
            # Initialize Agent
            agent = LLMWebAgent(llm=self.llm)
            
            # Initialize Runner
            runner = AgentRunner(env, agent, output_dir)
            
            # Execute with a hard timeout to prevent infinite hangs
            result = await asyncio.wait_for(
                runner.run_task(output_dir, task, max_steps=12),
                timeout=600  # 10 minute hard limit
            )
            
            if result.success:
                return True, None
                
            # If failed, compile the trajectory into a helpful error message for the Fixer
            error_details = "Autonomous Agent Failed to Complete Task.\n\nAgent Trajectory:\n"
            for i, step in enumerate(result.trajectory):
                error_details += f"  Step {i+1}: Action: {step.action.type}({step.action.target})\n"
                error_details += f"           Result: {step.info}\n"
            
            error_details += "\nThe agent got stuck or failed to achieve the goal using the rendered UI."
            return False, error_details
            
        except Exception as e:
            logger.error(f"Agent validation exception: {e}")
            return False, f"Agent validation framework error: {str(e)}"
        finally:
            if env:
                await env.stop()
