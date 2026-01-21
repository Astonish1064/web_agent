import json
from .interfaces import ISpecGenerator, IBackendGenerator, IFrontendGenerator, IEvaluatorGenerator, IInstrumentationGenerator
from .domain import WebsiteSpec, Task, DataModel, InterfaceDef, InstrumentationSpec, VariableRequirement, PageSpec

class MockSpecGenerator(ISpecGenerator):
    def generate(self, seed: str) -> WebsiteSpec:
        # Return a fixed spec for "bookstore" regardless of input, or handling simple logic
        return WebsiteSpec(
            seed=seed,
            task_instruction="Goal: Find and add a cheap book (under $20) to your cart.",
            tasks=[
                Task(id="task_1", description="Add a cheap book to cart", complexity=1, required_steps=["search", "add_to_cart"]),
                Task(id="task_2", description="Proceed to checkout", complexity=1, required_steps=["checkout"])
            ],
            data_models=[
                DataModel(name="Book", attributes={"title": "string", "price": "float", "id": "string"}),
                DataModel(name="Cart", attributes={"items": "List[Book]", "total": "float"})
            ],
            interfaces=[
                InterfaceDef(name="searchBooks", description="Search methods", parameters={"query": "string"}, return_type="Book[]"),
                InterfaceDef(name="addToCart", description="Add book to cart", parameters={"bookId": "string"}, return_type="void"),
                InterfaceDef(name="checkout", description="Process order", parameters={}, return_type="boolean")
            ],
            pages=[
                PageSpec(name="Home", filename="index.html", description="Landing page with search", required_interfaces=["searchBooks"]),
                PageSpec(name="Product Detail", filename="product.html", description="Details of a book", required_interfaces=["addToCart"]),
                PageSpec(name="Checkout", filename="checkout.html", description="Cart summary and payment", required_interfaces=["checkout"])
            ]
        )

class MockBackendGenerator(IBackendGenerator):
    def generate_logic(self, spec: WebsiteSpec, instr_spec: InstrumentationSpec = None) -> str:
        # Simulate logic generation via TCTDD
        # In a real implementation, this would loop LLM calls against tests.
        
        # Build dynamic injection code based on instr_spec
        injection_code = ""
        if instr_spec:
            for req in instr_spec.requirements:
                if req.set_in_function == "addToCart":
                    # In a real LLM, this would be inserted intelligently. 
                    # Here we simulate the LLM following the instruction.
                    injection_code += f"        localStorage.setItem('{req.variable_name}', JSON.stringify(true));"

        return """
// Generated Logic (Simulated TCTDD)
console.log("Initializing Bookstore Logic...");

const DB = {
    books: [
        {id: "1", title: "Python 101", price: 29.99},
        {id: "2", title: "Cheap Thrills", price: 9.99}
    ],
    cart: []
};

// Initialize State
if (!localStorage.getItem('books')) {
    localStorage.setItem('books', JSON.stringify(DB.books));
}
if (!localStorage.getItem('cart')) {
    localStorage.setItem('cart', JSON.stringify([]));
}
// Init Trajectory Log
if (!localStorage.getItem('trajectory_log')) {
    localStorage.setItem('trajectory_log', JSON.stringify([]));
}


function logTraj(type, detail) {
    const log = JSON.parse(localStorage.getItem('trajectory_log') || '[]');
    log.push({
        step: log.length + 1,
        timestamp: Date.now(),
        type: type,
        detail: detail
    });
    const logStr = JSON.stringify(log);
    localStorage.setItem('trajectory_log', logStr);

    // Auto-Save to Server
    fetch('/save_trajectory', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: logStr
    }).catch(err => console.error("Auto-save failed:", err));
}


// Unified Interface Implementation
window.searchBooks = function(query) {
    const books = JSON.parse(localStorage.getItem('books'));
    const results = books.filter(b => b.title.toLowerCase().includes(query.toLowerCase()));
    console.log("Search results:", results);
    return results;
};

window.addToCart = function(bookId) {
    const books = JSON.parse(localStorage.getItem('books'));
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    const book = books.find(b => b.id === bookId);
    if (book) {
        cart.push(book);
        localStorage.setItem('cart', JSON.stringify(cart));
        // Instrumentation for Evaluator
        // DYNAMIC INJECTION START
""" + injection_code + """
        // DYNAMIC INJECTION END

        // Legacy/Default Trajectory Recording (Environment Feature)
        logTraj('FUNCTION_CALL', { name: 'addToCart', args: [bookId] });

        console.log("Added to cart:", book.title);
    }
};
"""

class MockFrontendGenerator(IFrontendGenerator):
    def generate_page(self, spec: WebsiteSpec, page_spec: PageSpec, logic_code: str) -> str:
        # Build Navigation
        nav_html = "<nav><ul>"
        for p in spec.pages:
            nav_html += f'<li><a href="{p.filename}">{p.name}</a></li>'
        nav_html += "</ul></nav>"

        # Build Page Specific Content
        content_html = ""
        if page_spec.filename == "index.html":
            content_html = """
                <h1>Welcome to InfiniteWeb Bookstore</h1>
                <div id="search-box">
                    <input type="text" id="query" placeholder="Search for books...">
                    <button onclick="performSearch()">Search</button>
                </div>
                <div id="results"></div>
            """
        elif page_spec.filename == "product.html":
            content_html = """
                <h1>Product Details</h1>
                <div id="product-display">
                    <h2>Python 101</h2>
                    <p>Price: $29.99</p>
                    <button onclick="addToCart('1')">Add to Cart</button>
                </div>
            """
        elif page_spec.filename == "checkout.html":
             content_html = """
                <h1>Checkout</h1>
                <div id="cart-summary"></div>
                <button onclick="alert('Checkout not implemented in mock')">Pay Now</button>
            """

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{page_spec.name} - {spec.seed}</title>
    <!-- Explicitly load logic.js (Shared Logic) -->
    <script src="logic.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        nav ul {{ list-style-type: none; padding: 0; }}
        nav ul li {{ display: inline; margin-right: 10px; }}
        #task-banner {{
            background-color: #ffeb3b; 
            padding: 10px; 
            border: 1px solid #fbc02d; 
            margin-bottom: 20px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div id="task-banner">
        Current Task: {spec.task_instruction}
    </div>

    {nav_html}
    <hr>
    {content_html}

    <script>
        // Global Click Listener for Trajectory Recording
        document.addEventListener('click', function(event) {{
            const target = event.target;
            // Record minimal useful info
            const info = {{
                tagName: target.tagName,
                id: target.id,
                innerText: target.innerText ? target.innerText.substring(0, 20) : ""
            }};
            
            // Only log if logTraj is available (from logic.js)
            if (typeof logTraj === 'function') {{
                logTraj('DOM_CLICK', info);
            }}
        }});

        // UI Binding Functions (Mocking the connection between UI and Logic)
        function performSearch() {{
            const query = document.getElementById('query').value;
            // Call shared logic
            const results = window.searchBooks(query);
            
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = "";
            if (results.length === 0) {{
                resultsDiv.innerHTML = "<p>No results found.</p>";
            }} else {{
                results.forEach(book => {{
                    const div = document.createElement('div');
                    div.innerHTML = `<p><strong>${{book.title}}</strong> - $${{book.price}} <button onclick="addToCart('${{book.id}}')">Add to Cart</button></p>`;
                    resultsDiv.appendChild(div);
                }});
            }}
        }}

        function updateCartUI() {{
            const cart = JSON.parse(localStorage.getItem('cart') || '[]');
            }};
            if (window.logTraj) {{
                window.logTraj('DOM_CLICK', logDetail);
            }}
        }});
    </script>
</body>
</html>
"""

class MockEvaluatorGenerator(IEvaluatorGenerator):
    def generate_evaluator(self, spec: WebsiteSpec) -> str:
        return """
window.evaluateTask = function(taskId) {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    
    // In real system, this checks variables defined in InstrumentationSpec
    // For mock, we check the legacy or dynamic ones.
    
    if (taskId === 'task_1') {
        const hasCheapBook = cart.some(b => b.price < 20);
        // We might check 'last_action' or the dynamic variable if we knew what it was.
        // For simplicity of this mock, we assume success if cart has item.
        if (hasCheapBook) {
            return { success: true, score: 1.0, message: "Cheap book added!" };
        }
        return { success: false, score: 0.0, message: "Condition not met" };
    }
    return { success: false, score: 0, message: "Unknown task" };
};
"""

class MockInstrumentationGenerator(IInstrumentationGenerator):
    def generate_spec(self, spec: WebsiteSpec) -> InstrumentationSpec:
        # Simulate LLM analyzing the task and deciding to instrument 'addToCart'
        return InstrumentationSpec(requirements=[
            VariableRequirement(
                variable_name="task_1_item_added",
                set_in_function="addToCart",
                set_condition="Always"
            )
        ])
