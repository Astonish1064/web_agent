import asyncio
from playwright.async_api import async_playwright
import os

async def debug():
    output_dir = "output/mature_agents_v11_production"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        path = os.path.abspath(os.path.join(output_dir, "index.html"))
        url = f"file://{path}"
        await page.goto(url)
        
        props = await page.evaluate("""() => {
            if (typeof WebsiteSDK === 'undefined') return 'UNDEFINED';
            const allProps = [];
            for (let prop in WebsiteSDK) {
                allProps.append(prop + ": " + typeof WebsiteSDK[prop]);
            }
            // Also check prototypes
            let proto = Object.getPrototypeOf(WebsiteSDK);
            const protoProps = [];
            while (proto) {
                protoProps.push(...Object.getOwnPropertyNames(proto));
                proto = Object.getPrototypeOf(proto);
            }
            return {
                base: Object.keys(WebsiteSDK),
                proto: protoProps,
                stringified: JSON.stringify(WebsiteSDK)
            };
        }""")
        print(f"WebsiteSDK Inspection: {props}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
