
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
