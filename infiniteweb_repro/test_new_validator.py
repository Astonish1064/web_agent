
import asyncio
import os
import sys

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from src.agent.environments.env_validator import EnvironmentHealthChecker

async def main():
    checker = EnvironmentHealthChecker()
    output_dir = "/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro/output/mature_agents_v11_production"
    
    print("🔍 Testing product.html (known to have mocks)...")
    success, errors = await checker.validate_frontend(output_dir, "product.html")
    print(f"Result: {'PASS' if success else 'FAIL'}")
    if errors:
        print(f"Errors found: {errors}")

    print("\n🔍 Testing index.html...")
    success, errors = await checker.validate_frontend(output_dir, "index.html")
    print(f"Result: {'PASS' if success else 'FAIL'}")
    if errors:
        print(f"Errors found: {errors}")

if __name__ == "__main__":
    asyncio.run(main())
