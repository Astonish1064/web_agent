const fs = require('fs');
const { JSDOM } = require("jsdom");

// 1. Setup Input
// The Python runner passes the user code file path as the first argument
const userCodePath = process.argv[2];
if (!userCodePath) {
    console.error(JSON.stringify({ success: false, error: "No user code path provided" }));
    process.exit(1);
}

// 2. Mock Browser Environment (JSDOM)
const dom = new JSDOM(`<!DOCTYPE html><body></body>`, {
    url: "http://localhost/",
    runScripts: "dangerously",
    resources: "usable"
});

global.window = dom.window;
global.document = dom.window.document;
global.localStorage = {
    _data: {},
    getItem: function (key) { return this._data[key] || null; },
    setItem: function (key, value) { this._data[key] = String(value); },
    removeItem: function (key) { delete this._data[key]; },
    clear: function () { this._data = {}; }
};

// 3. Execution Wrapper
try {
    const userCode = fs.readFileSync(userCodePath, 'utf8');

    // We expect the user code to be backend logic + assertions
    // For TCTDD, this script usually looks like:
    //    ... logic.js content ...
    //    ... verify.js content ...

    // Evaluate the code in the JSDOM context
    dom.window.eval(userCode);

    // If we reached here without throwing, success!
    // We can also check if the user code returned a specific result object if needed.
    console.log(JSON.stringify({
        success: true,
        logs: [],
        message: "Execution completed successfully"
    }));

} catch (err) {
    console.log(JSON.stringify({
        success: false,
        error: err.toString(),
        stack: err.stack
    }));
}
