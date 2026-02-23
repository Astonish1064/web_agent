const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const OUTPUT_DIR = '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro/output/deepseek_v31_new_machine';

(async () => {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    console.log('🤖 [Reward Verification] Starting Manual Logic Trigger Test...');

    // Navigate to the configurator page
    const pageUrl = `file://${path.join(OUTPUT_DIR, 'configurator.html')}`;
    await page.goto(pageUrl, { waitUntil: 'domcontentloaded' });

    // Inject Evaluator class definition via script tag
    // This persists across evaluate calls
    const evaluatorScript = fs.readFileSync(path.join(OUTPUT_DIR, 'evaluator.js'), 'utf8');
    await page.addScriptTag({ content: evaluatorScript });

    console.log('🧪 Triggering Task 1 Logic Steps...');

    // Simulate the sequence of actions that SHOULD yield reward=1.0 for Task 1
    await page.evaluate(() => {
        // 1. Set Budget
        applyBudgetFilter(1500);
        // 2. Set Performance
        applyPerformanceFilter(); // Sets 'high' performance
        // 3. Select High-Performance CPU
        selectComponent('cpu', 2); // ID 2 = High Performance CPU
        // 4. Select High-Performance GPU
        selectComponent('gpu', 2); // ID 2 = High Performance GPU
    });

    // Check localStorage
    const storage = await page.evaluate(() => JSON.stringify(window.localStorage));
    console.log('💾 LocalStorage Content:', storage);

    // Run Evaluator directly (class is now global from addScriptTag)
    const score = await page.evaluate(async () => {
        const ev = new Evaluator();
        const results = await ev.evaluate();
        return results['task_1'];
    });

    console.log(`\n🏆 Evaluated Score for Task 1: ${score}`);

    if (score === true || score === 1.0) {
        console.log('✅ SUCCESS: Reward system is functioning correctly.');
    } else {
        console.error('❌ FAILURE: Reward is not 1.0 despite correct actions.');
    }

    await browser.close();
})();
