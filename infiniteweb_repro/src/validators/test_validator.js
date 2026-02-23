const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const VALIDATOR_PATH = path.join(__dirname, 'validate_logic.js');

// Test Case 1: Valid Code
const goodCode = `
class SDK {
    test() { return true; }
}
if (typeof window !== 'undefined') window.WebsiteSDK = new SDK();
`;
fs.writeFileSync('test_good.js', goodCode);

// Test Case 2: Invalid Code (No Export)
const badCode = `
class SDK {
    test() { return true; }
}
// Forgot export
`;
fs.writeFileSync('test_bad.js', badCode);

// Test Case 3: Syntax Error
const syntaxErrorCode = `
class SDK {
    test() { return true
}
`;
fs.writeFileSync('test_syntax.js', syntaxErrorCode);

console.log("Running Unit Tests for Validator...");

try {
    // 1. Expected Success
    const res1 = execSync(`node ${VALIDATOR_PATH} test_good.js`).toString();
    const json1 = JSON.parse(res1);
    if (json1.success) console.log("✅ Test 1 Passed (Good Code)");
    else console.error("❌ Test 1 Failed: Should pass but failed", json1);

    // 2. Expected Failure (Missing Export)
    const res2 = execSync(`node ${VALIDATOR_PATH} test_bad.js`).toString();
    const json2 = JSON.parse(res2);
    if (!json2.success && json2.type === 'MissingExport') console.log("✅ Test 2 Passed (Missing Export caught)");
    else console.error("❌ Test 2 Failed: Should fail with MissingExport", json2);

    // 3. Expected Failure (Syntax Error)
    const res3 = execSync(`node ${VALIDATOR_PATH} test_syntax.js`).toString();
    const json3 = JSON.parse(res3);
    if (!json3.success && json3.type === 'RuntimeError') console.log("✅ Test 3 Passed (Syntax Error caught)");
    else console.error("❌ Test 3 Failed: Should fail with RuntimeError", json3);

} catch (e) {
    console.error("Test Harness Error:", e);
} finally {
    // Cleanup
    if (fs.existsSync('test_good.js')) fs.unlinkSync('test_good.js');
    if (fs.existsSync('test_bad.js')) fs.unlinkSync('test_bad.js');
    if (fs.existsSync('test_syntax.js')) fs.unlinkSync('test_syntax.js');
}
