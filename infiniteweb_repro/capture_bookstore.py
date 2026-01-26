
import asyncio
import os
from src.agent.environments.env_validator import EnvironmentHealthChecker

async def capture_bookstore_screenshots():
    output_dir = "/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro/output/bookstore_v3"
    checker = EnvironmentHealthChecker()
    
    # Files to capture
    files = ["book.html", "index.html"]
    
    for filename in files:
        screenshot_name = f"{filename.split('.')[0]}_preview.png"
        screenshot_path = os.path.join(output_dir, screenshot_name)
        
        print(f"📸 Capturing {filename} -> {screenshot_path}")
        success, error = await checker.validate_frontend(
            output_dir, filename, screenshot_path=screenshot_path
        )
        
        if success:
            print(f"✅ Success: {screenshot_path}")
        else:
            print(f"❌ Failed: {error}")

if __name__ == "__main__":
    asyncio.run(capture_bookstore_screenshots())
