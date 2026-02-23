
import asyncio
from playwright.async_api import async_playwright
import sys
import os

# Adds src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.environments.a11y_processor import A11yProcessor

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. Load a simple HTML content that mimics our Task 1 failure (Products)
        html_content = """
        <html>
            <body>
                <header>
                    <input type="text" placeholder="Search products..." aria-label="Search">
                    <button>Search</button>
                    <a href="cart.html" aria-label="Cart">Cart</a>
                </header>
                <main>
                    <div class="product-card">
                        <img src="laptop.jpg" alt="UltraBook Pro 15" onclick="location.href='product.html'">
                        <h3>UltraBook Pro 15</h3>
                        <p>$899.99</p>
                    </div>
                    <div class="product-card">
                        <img src="cheap.jpg" alt="BudgetBook" onclick="location.href='product.html'">
                        <h3>BudgetBook</h3>
                        <p>$12.50</p>
                    </div>
                </main>
            </body>
        </html>
        """
        await page.set_content(html_content)
        
        # 2b. Inject IDs (Simulating PlaywrightEnvironment logic)
        await page.evaluate("""() => {
            let idCounter = 1;
            document.querySelectorAll('*').forEach(el => {
                const style = window.getComputedStyle(el);
                const tag = el.tagName.toLowerCase();
                const isInteractive = 
                    ['button', 'a', 'input', 'select', 'textarea'].includes(tag) ||
                    el.hasAttribute('onclick') || 
                    el.onclick ||
                    style.cursor === 'pointer' ||
                    ['button', 'link', 'textbox', 'checkbox', 'radio'].includes(el.getAttribute('role'));
                    
                if (isInteractive) {
                    const aid = idCounter++;
                    
                    // Priority for name: aria-label > placeholder > innerText > alt > title
                    let originalLabel = 
                        el.getAttribute('aria-label') || 
                        el.getAttribute('placeholder') || 
                        el.innerText || 
                        el.getAttribute('alt') || 
                        el.getAttribute('title') || 
                        '';
                    
                    originalLabel = originalLabel.replace(/\s+/g, ' ').trim();
                    
                    el.setAttribute('aria-label', `${originalLabel} --agent-id:${aid}--`);
                }
            });
        }""")

        # 3. Get CDP Session
        client = await page.context.new_cdp_session(page)
        await client.send("Accessibility.enable")
        cdp_snapshot = await client.send("Accessibility.getFullAXTree")
        
        # 4. Process
        processor = A11yProcessor()
        tree_text = processor.process(cdp_snapshot)
        
        print("NDUMP START")
        print(tree_text)
        print("NDUMP END")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
