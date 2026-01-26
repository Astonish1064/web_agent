import os
import json
from openai import OpenAI
from .interfaces import ILLMProvider

class CustomLLMProvider(ILLMProvider):
    def __init__(self, base_url="https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47/v1", api_key="EMPTY", model="/volume/pt-train/models/GLM-4.7"):
        """
        Initializes the LLM provider pointing to a custom endpoint.
        Assumes an OpenAI-compatible API (e.g. vLLM, TGI).
        """
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.model = model

    def prompt(self, prompt_text: str, system_prompt: str = "") -> str:
        """
        Sends a completion request to the LLM.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt_text})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=8192,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Error: {e}")
            return ""

    def prompt_json(self, prompt_text: str, system_prompt: str = "") -> dict:
        """
        Requests JSON output.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt_text})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=8192,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"LLM JSON Error (fallback to text): {e}")
            text = self.prompt(prompt_text, system_prompt)
            # Try to extract JSON from text if fallback occurred
            try:
                # Basic JSON extraction
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1 and end != 0:
                    return json.loads(text[start:end])
            except:
                pass
            return {}
