
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
        localStorage.setItem('task_1_item_added', JSON.stringify(true));
        // DYNAMIC INJECTION END

        // Legacy/Default Trajectory Recording (Environment Feature)
        logTraj('FUNCTION_CALL', { name: 'addToCart', args: [bookId] });

        console.log("Added to cart:", book.title);
    }
};
