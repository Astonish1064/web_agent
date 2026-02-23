import os
import json
from typing import List, Dict, Optional
from ..interfaces import ILLMProvider
from ..utils import clean_code_response

# Lazy import handling in resolve method to avoid heavy startup

class OpenHandsResolver:
    """
    An autonomous agent resolver that uses the official OpenHands SDK.
    """
    
    def __init__(self, llm: ILLMProvider, workspace_dir: str):
        self.llm = llm
        self.workspace_dir = workspace_dir
        
    async def resolve(self, task_description: str, error_log: str, spec_context: Dict) -> bool:
        """
        Runs an OpenHands session to solve the task.
        """
        print(f"🤖 [OpenHands] Activating SDK-based resolver...")
        
        try:
            # Disable LiteLLM telemetry to prevent hangs on import/init
            import os
            os.environ["LITELLM_TELEMETRY"] = "FALSE"
            # Force terminal width to prevent rich text formatting from wrapping to 1 char
            os.environ["COLUMNS"] = "120"
            
            from openhands.sdk import LocalConversation
            from openhands.sdk.agent import Agent
            from openhands.sdk.llm import LLM
            from openhands.sdk.tool import Tool

            # Import tool definitions to ensure they are registered
            import openhands.tools.terminal.definition
            import openhands.tools.file_editor.definition

            # Synchronize LLM config
            model_name = "gpt-4o" 
            try:
                if hasattr(self.llm, "model"):
                    model_name = f"openai/{self.llm.model}"
                
                if hasattr(self.llm, "client"):
                    # Configure LiteLLM (via Env vars) to use the same custom endpoint
                    if hasattr(self.llm.client, "base_url"):
                        os.environ["OPENAI_BASE_URL"] = str(self.llm.client.base_url)
                    if hasattr(self.llm.client, "api_key"):
                        os.environ["OPENAI_API_KEY"] = str(self.llm.client.api_key)
            except Exception as e:
                print(f"⚠️ [OpenHands] Warning: Could not sync LLM config: {e}")

            # Disable auto tool choice for vLLM compatibility
            os.environ["LITELLM_DROP_PARAMS"] = "True"
            
            print(f"🤖 [OpenHands] Initialization with model {model_name}...")
            # Configure tools using Tool specs (references built-in tools by name)
            # The Agent will instantiate the actual ToolDefinition classes using these specs
            # and the conversation state (which holds the working directory).
            tools = [
                Tool(name="terminal"),
                Tool(name="file_editor")
            ]
            print(f"🤖 [OpenHands] LLM Config: model={model_name}, base_url={os.environ.get('OPENAI_BASE_URL')}, api_key_set={'OPENAI_API_KEY' in os.environ}, tools_count={len(tools)}")
            # Plan: "I have a task failure... fix it until tests pass"
            goal = f"Fix the code for task '{task_description}' in this workspace. verification failed with error: {error_log}. Please fix the code."
            
            # Configure LLM to drop unsupported parameters like tool_choice="auto"
            oh_llm = LLM(
                model=model_name,
                drop_params=True,
                native_tool_calling=False # Fallback to prompt-based tools if vLLM doesn't support native tool calling without extra flags
            )

            agent = Agent(llm=oh_llm, tools=tools)

            # Using LocalConversation for repro environment
            # Signature: LocalConversation(agent, workspace_dir) based on error message
            cl = LocalConversation(agent, self.workspace_dir)
            cl.send_message(goal)
            # The agent autonomously executes actions until finished
            # We monitor for the final status
            final_obs = cl.run()
            print(f"🤖 [OpenHands] Result: {final_obs}")
            return True # Assuming success for now if it finishes
        except Exception as e:
            print(f"❌ [OpenHands] SDK Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _log_event(self, event):
        print(f"🤖 [OpenHands] Event: {event}")
