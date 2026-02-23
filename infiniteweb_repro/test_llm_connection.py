import os
os.environ["LITELLM_TELEMETRY"] = "FALSE"
import litellm
from openhands.sdk.llm import LLM

litellm.set_verbose = True


# Configuration from repro_glm4.py
base_url = "https://siflow-auriga.siflow.cn/siflow/auriga/skyinfer/wzhang/glm47-tool-fork/v1"
model_name = "openai/glm-4"
api_key = "EMPTY"

# Set environment variables as OpenHands/LiteLLM expects
os.environ["OPENAI_BASE_URL"] = base_url
os.environ["OPENAI_API_KEY"] = api_key
os.environ["LLM_MODEL"] = model_name

print(f"Testing LLM Connection...")
print(f"Model: {model_name}")
print(f"Base URL: {base_url}")
print(f"API Key: {api_key}")

try:
    print("Initializing LLM...")
    llm = LLM(model=model_name)
    print("sending completion request...")
    response = llm.completion(
        messages=[{"role": "user", "content": "Hello, are you working?"}]
    )
    print(f"Response: {response}")
    print("✅ LLM Connection Successful!")
except Exception as e:
    print(f"❌ LLM Connection Failed: {e}")
    import traceback
    traceback.print_exc()
