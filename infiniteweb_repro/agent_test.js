// agent_test.js - Simple Playwright test to verify Agent Accessibility
const { chromium } = require('playwright');
const path = require('path');

const OUTPUT_DIR = '/volume/pt-coder/users/lysun/kzheng/web_agent/infiniteweb_repro/output/deepseek_v31_system_test';

(async () => {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    console.log('🤖 [Agent Test] Starting Agent Accessibility Test...');

    // Navigate to the builder page
    const pageUrl = `file://${path.join(OUTPUT_DIR, 'builder.html')}`;
    console.log(`📍 Navigating to: ${pageUrl}`);
    await page.goto(pageUrl, { waitUntil: 'domcontentloaded' });

    // --- Task 1: Simulate Agent Interaction ---
    // Step 1: Find and interact with the budget slider
    const budgetSlider = await page.locator('#budget-slider');
    if (await budgetSlider.isVisible()) {
        console.log('✅ Found budget slider by ID.');
        await budgetSlider.fill('2000');
        console.log('✅ Set budget to $2000.');
    } else {
        console.error('❌ Budget slider NOT FOUND.');
    }

    // Step 2: Select a category (GPU)
    const gpuTab = await page.locator('button[data-category="gpu"]');
    if (await gpuTab.isVisible()) {
        console.log('✅ Found GPU category tab.');
        await gpuTab.click();
        console.log('✅ Clicked GPU tab.');
    } else {
        console.error('❌ GPU tab NOT FOUND.');
    }

    // Step 3: Wait for components to load and click one
    // We wait briefly for JS to populate the grid
    try {
        const componentCard = await page.locator('.component-card').first();
        await componentCard.waitFor({ state: 'visible', timeout: 3000 });
        console.log('✅ Found component card (JS populated successfully).');

        // Check if it has an Add button
        const addBtn = await componentCard.locator('.add-btn');
        if (await addBtn.isVisible()) {
            await addBtn.click();
            console.log('✅ Clicked Add button on component.');
        }
    } catch (e) {
        console.warn('⚠️ No component cards appeared (JS logic might not have populated content or logic.js error).');
    }

    // Step 5: Check for accessibility issues (missing role/tabindex)
    const clickableDivs = await page.locator('div[data-action]').all();
    let accessibilityIssues = 0;
    for (const div of clickableDivs) {
        const role = await div.getAttribute('role');
        const tabindex = await div.getAttribute('tabindex');
        if (!role || !tabindex) {
            accessibilityIssues++;
            console.warn(`⚠️ Accessibility Issue: Found clickable div without role="${role}" or tabindex="${tabindex}"`);
        }
    }
    if (accessibilityIssues > 0) {
        console.log(`\n🔴 Total A11y Issues: ${accessibilityIssues} clickable divs missing role/tabindex attributes.`);
    } else {
        console.log('\n🟢 All clickable divs have proper accessibility attributes.');
    }

    await browser.close();
    console.log('\n🤖 [Agent Test] Test Completed.');
})();
