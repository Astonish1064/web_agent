const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    // Listen for page errors (uncaught exceptions)
    page.on('pageerror', error => {
        console.error(`🔴 PAGE ERROR: ${error.message}`);
    });

    console.log('🤖 [Fixed Env Test] Navigating to http://localhost:8081/build-editor.html');
    await page.goto('http://localhost:8081/build-editor.html', { waitUntil: 'networkidle' });

    // Step 1: Check if WebsiteSDK is available
    const sdkAvailable = await page.evaluate(() => typeof window.WebsiteSDK !== 'undefined');
    console.log(`🔍 WebsiteSDK Available: ${sdkAvailable}`);

    if (!sdkAvailable) {
        console.error('❌ FATAL: WebsiteSDK is not defined on the window object.');
        process.exit(1);
    }

    // Step 2: Try to click a button that uses WebsiteSDK
    console.log('👆 Clicking "Check Compatibility" button...');
    try {
        await page.click('[data-action="checkCompatibility"]');
        console.log('✅ Click succeeded (No immediate crash).');
    } catch (e) {
        console.error(`❌ Click failed: ${e.message}`);
    }

    // Step 3: Wait a bit to ensure no async errors pop up
    await page.waitForTimeout(1000);

    // Step 4: Verify Logic functionality - check if logic.js loaded properly
    const catalogSize = await page.evaluate(() => {
        // Use the actual method name from logic.js
        if (WebsiteSDK.getCompatibleComponents) {
            return Object.keys(WebsiteSDK.getCompatibleComponents('CPU') || {}).length;
        }
        return -1;
    });

    console.log(`📦 Catalog Size (CPUs) via SDK: ${catalogSize}`);

    if (catalogSize > 0) {
        console.log('✅ logic.js loaded and data is accessible.');
    } else {
        console.warn('⚠️ Could not verify catalog data via SDK.');
    }

    await browser.close();
})();
