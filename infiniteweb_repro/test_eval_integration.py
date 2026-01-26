import asyncio
import os
from playwright.async_api import async_playwright
from src.agent.evaluation.web_evaluator import WebEvaluator

async def test_evaluator():
    website_dir = "output/bookstore_v3"
    evaluator = WebEvaluator(website_dir)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to a real file to allow localStorage access
        abs_path = os.path.abspath(os.path.join(website_dir, "index.html"))
        await page.goto(f"file://{abs_path}")
        
        await page.evaluate("""() => {
            localStorage.setItem('task1_searchCompleted', 'true');
            localStorage.setItem('task1_cartAddition', 'true');
        }""")
        
        # Test evaluation for task_1
        score = await evaluator.evaluate_task(page, "task_1")
        print(f"Task 1 score (expected 1.0): {score}")
        
        # Test evaluation for task_2 (should be 0.0)
        score = await evaluator.evaluate_task(page, "task_2")
        print(f"Task 2 score (expected 0.0): {score}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_evaluator())
