const fs = require('fs');
const vm = require('vm');
const path = require('path');

// 1. Parse Arguments
const logicFilePath = process.argv[2];
if (!logicFilePath) {
    console.log(JSON.stringify({ success: false, error: "Usage: node validate_logic.js <path_to_logic.js>" }));
    process.exit(1);
}

try {
    const code = fs.readFileSync(logicFilePath, 'utf8');

    // 2. Setup Sandbox Context
    const sandbox = {
        window: {}, // The target for WebsiteSDK
        module: { exports: {} }, // For Node compatibility
        exports: {},
        localStorage: {
            getItem: () => null,
            setItem: () => { },
            removeItem: () => { },
            clear: () => { }
        },
        console: {
            log: () => { }, // Suppress logs
            error: () => { },
            warn: () => { }
        },
        setTimeout: () => { },
        clearTimeout: () => { }
    };

    // 3. Execute Code in Sandbox
    vm.createContext(sandbox);

    try {
        // Execute the code
        vm.runInContext(code, sandbox, { timeout: 1000 }); // 1s timeout to prevent infinite loops
    } catch (runtimeError) {
        console.log(JSON.stringify({
            success: false,
            error: `Runtime Error: ${runtimeError.message}`,
            type: "RuntimeError"
        }));
        process.exit(0); // Exit cleanly with error JSON
    }

    // 4. Validate Exports
    const hasWindowExport = sandbox.window && sandbox.window.WebsiteSDK;
    const hasModuleExport = sandbox.module && sandbox.module.exports &&
        (typeof sandbox.module.exports === 'function' || Object.keys(sandbox.module.exports).length > 0);

    // Strict Requirement: Must have window.WebsiteSDK for frontend to work
    if (!hasWindowExport) {
        console.log(JSON.stringify({
            success: false,
            error: "CRITICAL: logic.js does not export 'WebsiteSDK' to 'window'. Frontend will fail with ReferenceError.",
            type: "MissingExport"
        }));
        process.exit(0);
    }

    // 5. Structure Validation (Optional but good)
    const sdk = sandbox.window.WebsiteSDK;
    const keys = Object.keys(sdk).concat(Object.getOwnPropertyNames(Object.getPrototypeOf(sdk) || {}));

    // Filter out constructor and standard object props
    const functionKeys = keys.filter(k => k !== 'constructor' && k !== '__defineGetter__' && k !== '__defineSetter__' && k !== 'hasOwnProperty');

    if (functionKeys.length === 0) {
        console.log(JSON.stringify({
            success: false,
            error: "WebsiteSDK object exists but appears empty (no functions found).",
            type: "EmptySDK"
        }));
        process.exit(0);
    }

    // Success
    console.log(JSON.stringify({
        success: true,
        functions: functionKeys
    }));
    process.exit(0);

} catch (err) {
    console.log(JSON.stringify({
        success: false,
        error: `System Error: ${err.message}`,
        type: "SystemError"
    }));
    process.exit(1);
}
