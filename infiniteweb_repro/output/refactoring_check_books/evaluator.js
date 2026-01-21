
        function evaluate_task_search_buy() {
            const added = localStorage.getItem('inst_added_to_cart') === 'true';
            const checkout = localStorage.getItem('inst_checkout_completed') === 'true';
            
            if (checkout) return 1.0;
            if (added) return 0.5;
            return 0.0;
        }
        