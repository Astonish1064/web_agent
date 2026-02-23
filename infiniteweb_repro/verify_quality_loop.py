import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.generators.backend_generator import LLMBackendGenerator
from src.llm import CustomLLMProvider

@dataclass
class Task:
    id: str
    description: str

@dataclass
class DataModel:
    name: str
    attributes: Dict

@dataclass
class Interface:
    name: str
    parameters: List[str]
    description: str

@dataclass
class Spec:
    seed: str
    tasks: List[Task]
    data_models: List[DataModel]
    interfaces: List[Interface]

def test_quality_loop():
    # Setup mock LLM and Generator
    # Use a real LLM if possible, or mock it to fail once.
    # For now, let's use the real configured LLM to see it in action.
    llm = CustomLLMProvider(
        base_url="http://10.166.90.27:8000/v1",
        model="/volume/pt-train/models/DeepSeek-V3.1"
    )
    gen = LLMBackendGenerator(llm)
    
    spec = Spec(
        seed="Weather Dashboard",
        tasks=[Task("t1", "Fetch and display weather for a city")],
        data_models=[DataModel("Weather", {"city": "string", "temp": "number"})],
        interfaces=[Interface("getWeather", ["city"], "Returns weather data")]
    )
    
    print("🚀 Testing Backend Quality Loop...")
    try:
        code = gen.generate_logic(spec)
        print("\n=== Generated Code Snippet ===")
        print(code[:500] + "...")
        print("\n✅ Test Completed Successfully!")
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")

if __name__ == "__main__":
    test_quality_loop()
