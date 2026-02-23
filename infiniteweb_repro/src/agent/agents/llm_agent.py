import json
import asyncio
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
        history_lines = []
        for i, a in enumerate(history[-5:]):
            line = f"- {a.type}({a.target or ''}, {a.value or ''})"
            # If this is the LAST action and the observation says it failed, mark it.
            # Note: history items are ordered. The last item in history corresponds to the action just taken.
            # We assume 'observation' reflects the state AFTER history[-1].
            if i == len(history[-5:]) - 1:
                # Check success of the *previous* action (which is this one)
                if hasattr(observation, 'last_action_success') and not observation.last_action_success:
                     line += " (FAILED)"
            history_lines.append(line)
        history_str = "\n".join(history_lines)
        
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
        
        # 3. Call LLM (offload sync call to thread pool to avoid blocking event loop)
        try:
            response = await asyncio.to_thread(
                self.llm.prompt_json, user_prompt, AGENT_SYSTEM_PROMPT
            )
            
            if not response or 'action' not in response:
                logger.error(f"LLM returned invalid action format: {response}")
                return Action(type="fail", reasoning="Invalid LLM response format")
                
            action_data = response['action']
            return Action(
                type=action_data.get('type', 'wait'),
                target=action_data.get('target'),
                value=str(action_data.get('value', '')),
                reasoning=response.get('thought')  # Map 'thought' (Reflexion) to reasoning
            )
            
        except Exception as e:
            logger.error(f"Error in Agent decision: {e}")
            return Action(type="fail", reasoning=f"Exception during LLM call: {e}")
