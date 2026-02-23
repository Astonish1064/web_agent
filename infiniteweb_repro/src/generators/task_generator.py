"""
LLMTaskGenerator - Phase 1.1 Implementation

Generates user tasks from a website seed using PROMPT_TASK_GENERATION.
"""
import json
from dataclasses import dataclass
from typing import List

from ..interfaces import ITaskGenerator, ILLMProvider
from ..prompts.library import PROMPT_TASK_GENERATION
from ..utils import clean_json_response, with_retry
from ..validation import SchemaValidator

@dataclass
class TaskConfig:
    """Configuration for task generation."""
    website_type: str
    task_count_min: int = 3
    task_count_max: int = 7
    min_steps: int = 3
    max_steps: int = 8

from ..domain import Task


class LLMTaskGenerator(ITaskGenerator):
    # ... (skipping __init__ and generate to keep context clear, assuming they match)
    """Generates tasks using LLM with PROMPT_TASK_GENERATION."""
    
    def __init__(self, llm: ILLMProvider):
        self.llm = llm
    
    @with_retry(max_retries=3)
    def generate(self, seed: str, config: TaskConfig) -> List[Task]:
        """
        Generate tasks based on seed and configuration.
        
        Uses PROMPT_TASK_GENERATION from library with:
        - {website_type}: The type of website
        - {task_count_range}: Range like "3-7"
        - {min_steps}: Minimum steps per task
        - {max_steps}: Maximum steps per task
        """
        # Format the prompt
        task_count_range = f"{config.task_count_min}-{config.task_count_max}"
        
        prompt = PROMPT_TASK_GENERATION.format(
            website_type=config.website_type,
            task_count_range=task_count_range,
            min_steps=config.min_steps,
            max_steps=config.max_steps
        )
        
        # Call LLM
        response = self.llm.prompt(prompt)
        
        # Parse response
        return self._parse_response(response, config)
    
    def _parse_response(self, response: str, config: TaskConfig) -> List[Task]:
        """Parse LLM response into GeneratedTask objects."""
        data = clean_json_response(response)
        if not data:
            print(f"Task Parsing Failed. Response: {response}")
            return []
        
        # Debug: show what we parsed
        print(f"[DEBUG] Parsed JSON keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            
        tasks_data = data.get("tasks", [])
        print(f"[DEBUG] Found {len(tasks_data)} tasks in JSON")
        
        # Robustness: Validate Schema
        if not SchemaValidator.validate_tasks(tasks_data):
            print(f"Task Verification Failed. Structure invalid.")
            return []
        
        tasks = []
        for i, task_data in enumerate(tasks_data):
            task = self._sanitize_task(task_data, i, config)
            if task:
                tasks.append(task)
        
        return tasks
    
    def _sanitize_task(self, data: dict, index: int, config: TaskConfig) -> Task:
        """Sanitize and validate a single task."""
        if not isinstance(data, dict):
            return None
            
        # Extract with defaults
        task_id = data.get("id", f"task_{index + 1}")
        name = data.get("name", data.get("description", "Unnamed Task")[:50])
        description = data.get("description", "No description provided")
        steps = data.get("steps", [])
        
        # Ensure steps is a list
        if not isinstance(steps, list):
            steps = []
        
        # Validate step count (warn but don't reject)
        if len(steps) < config.min_steps or len(steps) > config.max_steps:
            # Still accept but log could go here
            pass
        
        return Task(
            id=task_id,
            name=name,
            description=description,
            steps=steps
        )
