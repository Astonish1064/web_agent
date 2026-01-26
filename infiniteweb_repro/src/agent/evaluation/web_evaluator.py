import os
import logging
from playwright.async_api import Page

logger = logging.getLogger("agent.evaluation")

class WebEvaluator:
    """Executes the generated evaluator.js within the browser page."""
    
    def __init__(self, website_dir: str):
        self.website_dir = website_dir
        self.evaluator_script = ""
        self._load_evaluator()

    def _load_evaluator(self):
        eval_path = os.path.join(self.website_dir, "evaluator.js")
        if os.path.exists(eval_path):
            with open(eval_path, "r") as f:
                self.evaluator_script = f.read()
        else:
            logger.warning(f"No evaluator.js found at {eval_path}")

    async def evaluate_task(self, page: Page, task_id: str) -> float:
        """
        Runs the evaluator and returns a score (0.0 to 1.0) for the task.
        Currently returns 1.0 if task_id in results is truthy.
        """
        if not self.evaluator_script:
            return 0.0
            
        try:
            # 1. Inject script and run evaluator
            # We wrap the class definition and instantiation in an async IIFE
            eval_call = f"""
            (async () => {{
                {self.evaluator_script}
                const ev = new Evaluator();
                const results = await ev.evaluate();
                return results;
            }})()
            """
            results = await page.evaluate(eval_call)
            
            # 2. Extract result for specific task
            if isinstance(results, dict):
                score = results.get(task_id, 0)
                # Ensure it's a float
                try:
                    return float(score)
                except:
                    return 1.0 if score else 0.0
            return 0.0
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return 0.0
