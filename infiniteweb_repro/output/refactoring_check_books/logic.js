
        window.logic = {
            _load: function(key) { return JSON.parse(localStorage.getItem(key) || '[]'); },
            _save: function(key, val) { localStorage.setItem(key, JSON.stringify(val)); },
            
            searchBooks: function(query) {
                // Mock database
                const db = [
                    {id: "b1", title: "Learning Python", price: 29.99},
                    {id: "b2", title: "Advanced AI", price: 49.99}
                ];
                return db.filter(b => b.title.toLowerCase().includes(query.toLowerCase()));
            },
            
            addToCart: function(bookId, quantity) {
                const cart = this._load('cart');
                cart.push({bookId, quantity});
                this._save('cart', cart);
                
                // Instrumentation for Evaluator
                localStorage.setItem('inst_added_to_cart', 'true');
            },
            
            getCart: function() {
                return this._load('cart');
            },
            
            checkout: function() {
                const cart = this._load('cart');
                if(cart.length === 0) throw new Error("Cart is empty");
                this._save('cart', []); // Clear cart
                this._save('last_order', {id: Date.now(), items: cart, status: 'confirmed'});
                
                // Instrumentation
                localStorage.setItem('inst_checkout_completed', 'true');
                return {status: 'success'};
            }
        };
        