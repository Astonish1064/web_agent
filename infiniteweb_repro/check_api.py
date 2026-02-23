import requests
import json
import sys

base_url = "https://siflow-zhuoguang.siflow.cn/siflow/zhuoguang/skyinfer/chao/dpskv32-tp8dp1-h20-service-fork/v1"

try:
    response = requests.get(f"{base_url}/models")
    if response.status_code == 200:
        data = response.json()
        print("Successfully connected to API.")
        print("Available models:")
        for model in data.get('data', []):
            print(f" - {model.get('id')}")
    else:
        print(f"Failed to get models. Status code: {response.status_code}")
        print(response.text)
        
        # Try a simple completion request to see if it gives an error about model name
        print("\nTrying a chat completion with a dummy model name...")
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        res2 = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        print(f"Status: {res2.status_code}")
        print(res2.text)

except Exception as e:
    print(f"Error connecting to API: {e}")
