import os
from openai import OpenAI
from .interfaces import ILLMProvider

class CustomLLMProvider(ILLMProvider):
    def __init__(self, base_url="http://10.166.75.190:8000/v1", api_key="EMPTY", model="/volume/pt-train/models/Qwen3-Coder-480B-A35B-Instruct"):
        """
        Initializes the LLM provider pointing to a custom endpoint.
        Assumes an OpenAI-compatible API (e.g. vLLM, TGI).
        """
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.model = model

    def prompt(self, prompt_text: str) -> str:
        """
        Sends a completion request to the LLM.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.7,
                max_tokens=8192,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Error: {e}")
            return ""

    def prompt_json(self, prompt_text: str) -> str:
        """
        Requests JSON output (if supported by backend, or just via prompt engineering).
        We force JSON mode in the API call if possible.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.2,
                max_tokens=8192,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
             # Fallback to normal prompt if json_object not supported by backend
            print(f"LLM JSON Error (fallback to text): {e}")
            return self.prompt(prompt_text)
