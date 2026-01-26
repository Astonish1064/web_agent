import json
import logging
from typing import List, Optional
from ..interfaces import IWebAgent
from ..domain import Action, Observation
from src.interfaces import ILLMProvider
from src.domain import Task
from .prompts import AGENT_SYSTEM_PROMPT, AGENT_USER_PROMPT_TEMPLATE

logger = logging.getLogger("agent.llm")

class LLMWebAgent(IWebAgent):
    """An LLM-powered Web Agent that uses a provider to decide actions."""
    
    def __init__(self, llm: ILLMProvider, use_instrumentation: bool = True):
        self.llm = llm
        self.use_instrumentation = use_instrumentation
        self.history = []

    def reset(self):
        self.history = []

    async def decide(self, observation: Observation, task: Task, history: List[Action]) -> Action:
        """Determines the next action using the LLM."""
        
        # 1. Prepare history string
        history_str = "\n".join([f"- {a.type}({a.target or ''}, {a.value or ''})" for a in history[-5:]])
        
        # 2. Prepare instrumentation info
        instr_info = "HIDDEN (Simulating human-level perception)"
        if self.use_instrumentation:
            instr_info = json.dumps(observation.instrumentation_state, indent=2)
        
        # 3. Prepare user prompt
        from datetime import datetime
        user_prompt = AGENT_USER_PROMPT_TEMPLATE.format(
            task_name="Task " + task.id,
            task_goal=getattr(task, 'description', 'No detailed instruction'),
            task_steps=getattr(task, 'required_steps', []),
            url=observation.url,
            page_title=observation.page_title,
            current_date=datetime.now().strftime("%Y-%m-%d (%A)"),
            instrumentation=instr_info,
            a11y_tree=observation.a11y_tree or "No A11y Tree available",
            dom_tree=observation.dom_tree[:5000], # Trucate for token limit
            history=history_str or "No actions yet"
        )
        
        # 3. Call LLM
        try:
            response = self.llm.prompt_json(user_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
            
            if not response or 'action' not in response:
                logger.error(f"LLM returned invalid action format: {response}")
                return Action(type="fail", reasoning="Invalid LLM response format")
                
            action_data = response['action']
            return Action(
                type=action_data.get('type', 'wait'),
                target=action_data.get('target'),
                value=str(action_data.get('value', '')),
                reasoning=response.get('reasoning')
            )
            
        except Exception as e:
            logger.error(f"Error in Agent decision: {e}")
            return Action(type="fail", reasoning=f"Exception during LLM call: {e}")
