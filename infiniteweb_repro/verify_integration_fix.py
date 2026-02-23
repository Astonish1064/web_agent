
import asyncio
import os
import sys
import shutil

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import CustomLLMProvider
from src.async_pipeline import AsyncWebGenPipeline
from src.domain import GenerationContext, WebsiteSpec

# Mock classes to satisfy init
class MockGen:
    pass

async def main():
    print("🚀 Starting Integration Fix Verification (Real Model: 10.166.75.190)...")
    
    # 1. Setup Environment
    output_dir = "test_output/integration_fix_verify_real"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Initialize Real LLM
    llm = CustomLLMProvider(
        base_url="http://10.166.75.190:8000/v1",
        model="/volume/pt-train/models/DeepSeek-V3.1"
    )
    
    # 3. Create Pipeline (partial init just for _run_integration_validation)
    pipeline = AsyncWebGenPipeline(
        *[MockGen() for _ in range(9)], # 9 dummies
        llm=llm
    )
    
    # 4. Prepare Context with BUGGY Integration
    context = GenerationContext(seed="test_shop", output_dir=output_dir)
    context.spec = WebsiteSpec(seed="test_shop")
    
    # 4.1 Backend: Implements "addItem"
    backend_code = """
    class BusinessLogic {
        constructor() { this.cart = []; }
        addItem(id, qty) { 
            this.cart.push({id, qty}); 
            console.log("Added item " + id);
            return true;
        }
        _initStorage() {}
    }
    if (typeof window !== 'undefined') { window.WebsiteSDK = new BusinessLogic(); }
    if (typeof module !== 'undefined') { module.exports = BusinessLogic; }
    """
    context.backend_code = backend_code
    with open(os.path.join(output_dir, "logic.js"), "w") as f:
        f.write(backend_code)
        
    # 4.2 Frontend: Calls "addToCart" (WRONG NAME)
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="logic.js"></script>
    </head>
    <body>
        <h1>Shop</h1>
        <button id="btn" onclick="tryBuy()">Buy</button>
        <div id="result"></div>
        <script>
            function tryBuy() {
                try {
                    // BUG: Calling addToCart instead of addItem
                    WebsiteSDK.addToCart('123', 1);
                    document.getElementById('result').innerText = 'Success';
                } catch (e) {
                    console.error("Integration Error: " + e.message);
                    document.getElementById('result').innerText = 'Error: ' + e.message;
                    throw e; // Ensure validator catches it
                }
            }
            // Auto-trigger for validator
            window.onload = function() {
                setTimeout(tryBuy, 500);
            };
        </script>
    </body>
    </html>
    """
    context.generated_pages = {"index.html": html_content}
    with open(os.path.join(output_dir, "index.html"), "w") as f:
        f.write(html_content)
        
    print("📝 setup files with INTENTIONAL BUG: Frontend calls 'addToCart', Backend has 'addItem'.")
    
    # 5. Run Validation Loop
    print("🧪 Running _run_integration_validation (should trigger fix loop)...")
    await pipeline._run_integration_validation(context)
    
    # 6. Verify Result
    with open(os.path.join(output_dir, "index.html"), "r") as f:
        new_html = f.read()
        
    if "addItem" in new_html:
        print("\n✅ VERIFICATION PASSED: Frontend was patched to use 'addItem'!")
    elif "addToCart" not in new_html:
        print("\n✅ VERIFICATION PASSED: Frontend removed the broken call.")
    else:
        print("\n❌ VERIFICATION FAILED: 'addToCart' still present.")
        print(new_html)

if __name__ == "__main__":
    asyncio.run(main())
