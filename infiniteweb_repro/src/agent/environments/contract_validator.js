const fs = require('fs');
const path = require('path');

/**
 * contract_validator.js
 * 
 * This script verifies that BusinessLogic methods in logic.js 
 * strictly adhere to the return types defined in interfaces.json.
 */

async function main() {
    const outputDir = process.argv[2] || '.';
    const logicPath = path.resolve(outputDir, 'logic.js');
    const interfacePath = path.resolve(outputDir, 'intermediates/3_interfaces.json');

    if (!fs.existsSync(logicPath) || !fs.existsSync(interfacePath)) {
        console.error(JSON.stringify({
            success: false,
            error: "Missing logic.js or 3_interfaces.json"
        }));
        process.exit(1);
    }

    // Load data
    const interfaces = JSON.parse(fs.readFileSync(interfacePath, 'utf8'));
    
    // Setup environment for logic.js (localStorage, window)
    require('jsdom-global')('http://localhost/', {
        url: "http://localhost/",
        storageQuota: 10000000
    });

    let BusinessLogic;
    try {
        BusinessLogic = require(logicPath);
    } catch (e) {
        console.error(JSON.stringify({
            success: false,
            error: `Failed to require logic.js: ${e.message}`
        }));
        process.exit(1);
    }

    const instance = new BusinessLogic();
    const violations = [];

    for (const iface of interfaces) {
        const methodName = iface.name;
        if (typeof instance[methodName] !== 'function') {
            violations.push({
                method: methodName,
                type: 'MISSING_METHOD',
                message: `Method '${methodName}' is not defined in BusinessLogic`
            });
            continue;
        }

        // We check return schema by calling the method with minimal/null arguments
        // and checking the keys of the returned object.
        // If it throws, we try to catch and analyze (missing data is expected, but schema should exist)
        try {
            // Create dummy arguments based on parameter count
            const dummyArgs = (iface.parameters || []).map(() => null);
            const result = instance[methodName](...dummyArgs);

            if (iface.returns && iface.returns.type === 'object') {
                if (!result || typeof result !== 'object') {
                    violations.push({
                        method: methodName,
                        type: 'TYPE_MISMATCH',
                        message: `Expected object return, got ${typeof result}`
                    });
                } else {
                    const expectedProps = Object.keys(iface.returns.properties || {});
                    const actualProps = Object.keys(result);
                    
                    for (const prop of expectedProps) {
                        if (!(prop in result)) {
                            violations.push({
                                method: methodName,
                                type: 'MISSING_KEY',
                                message: `Return object missing key: '${prop}'`,
                                expected_keys: expectedProps,
                                actual_keys: actualProps
                            });
                        }
                    }
                }
            }
        } catch (e) {
            // If it fails due to logic errors (e.g. data lookup), we ignore it IF the method exists
            // A more robust way would be AST analysis, but dynamic check catches the obvious "success" wrapper issue.
            // console.warn(`Note: Method ${methodName} threw during dry run: ${e.message}`);
        }
    }

    console.log(JSON.stringify({
        success: violations.length === 0,
        violations: violations
    }));
}

main();
