import os
import json
import time
import httpx
from openai import OpenAI
from .interfaces import ILLMProvider

class CustomLLMProvider(ILLMProvider):
    def __init__(self, base_url="https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47/v1", api_key="EMPTY", model=None):
        """
        Initializes the LLM provider pointing to a custom endpoint.
        Assumes an OpenAI-compatible API (e.g. vLLM, TGI).
        """
        # Set a strict httpx timeout: 30s connect, 120s read, 120s write
        http_client = httpx.Client(
            timeout=httpx.Timeout(connect=30.0, read=300.0, write=300.0, pool=30.0),
            verify=False # Disable SSL verification for internal APIs
        )
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            http_client=http_client,
        )
        
        # Auto-detect model if not provided
        if model is None or model == "/volume/pt-train/models/GLM-4.7":
            try:
                models = self.client.models.list()
                if models.data:
                    self.model = models.data[0].id
                    print(f"🤖 [LLM] Auto-detected model: {self.model} at {base_url}")
                else:
                    self.model = model or "default"
            except Exception as e:
                print(f"⚠️ [LLM] Failed to auto-detect model at {base_url}: {e}")
                self.model = model or "default"
        else:
            self.model = model
            
        self.response_callback = None

    def prompt(self, prompt_text: str, system_prompt: str = "") -> str:
        """
        Sends a completion request to the LLM.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt_text})

        print(f"🔄 [LLM] prompt() calling {self.model}... (prompt_len={len(prompt_text)})", flush=True)
        
        # 动态计算 max_tokens：如果 prompt 很长，就减少 max_tokens，保证总长度不超过 32000
        # 假设 1 个字符大约等于 0.3 个 token（保守估计）
        estimated_prompt_tokens = int(len(prompt_text) * 0.3)
        # 预留 32000 的总上下文，减去 prompt 占用的 token，剩下的给 max_tokens
        # 至少保留 4096 个 token 用于生成，最多不超过 32000
        dynamic_max_tokens = max(4096, min(32000, 32000 - estimated_prompt_tokens))
        
        t0 = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=dynamic_max_tokens,
            )
            elapsed = time.time() - t0
            content = response.choices[0].message.content
            print(f"✅ [LLM] prompt() returned in {elapsed:.1f}s (response_len={len(content)})", flush=True)
            if self.response_callback:
                self.response_callback(content)
            return content
        except Exception as e:
            elapsed = time.time() - t0
            print(f"❌ [LLM] prompt() failed after {elapsed:.1f}s: {e}", flush=True)
            raise e  # Propagate error for retry logic

    def prompt_json(self, prompt_text: str, system_prompt: str = "") -> dict:
        """
        Requests JSON output.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt_text})

        print(f"🔄 [LLM] prompt_json() calling {self.model}... (prompt_len={len(prompt_text)})", flush=True)
        
        # 动态计算 max_tokens
        estimated_prompt_tokens = int(len(prompt_text) * 0.3)
        dynamic_max_tokens = max(4096, min(32000, 32000 - estimated_prompt_tokens))
        
        t0 = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=dynamic_max_tokens,
                response_format={"type": "json_object"}
            )
            elapsed = time.time() - t0
            content = response.choices[0].message.content
            print(f"✅ [LLM] prompt_json() returned in {elapsed:.1f}s (response_len={len(content)})", flush=True)
            if self.response_callback:
                self.response_callback(content)
            return json.loads(content, strict=False)
        except Exception as e:
            elapsed = time.time() - t0
            print(f"❌ [LLM] prompt_json() failed after {elapsed:.1f}s: {e}", flush=True)
            text = self.prompt(prompt_text, system_prompt)
            # Try to extract JSON from text if fallback occurred
            try:
                # Basic JSON extraction
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1 and end != 0:
                    return json.loads(text[start:end], strict=False)
            except:
                pass
            return {}

