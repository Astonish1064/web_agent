import json
import logging
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from ..interfaces import ILLMProvider
from ..domain import WebsiteSpec, Task, PageSpec
from ..prompts.library import PROMPT_GOLDEN_PATH_GENERATION

logger = logging.getLogger("generators.verification")

class VerificationGenerator:
    def __init__(self, llm: ILLMProvider):
        self.llm = llm

    def _extract_valid_action_space(self, html_content: str) -> List[str]:
        """Extracts a list of valid interactive selectors from the HTML."""
        valid_selectors = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. Define interactive tags
            interactive_tags = ['a', 'button', 'input', 'select', 'textarea', 'details', 'summary']
            
            # 2. Find all candidates
            candidates = soup.find_all(lambda tag: (
                tag.name in interactive_tags or 
                tag.has_attr('onclick') or 
                tag.get('role') == 'button' or
                tag.get('tabindex') == '0'
            ))
            
            for tag in candidates:
                # Skip hidden/invisible elements
                if tag.get('type') == 'hidden' or 'display: none' in tag.get('style', ''):
                    continue
                if not tag.get_text(strip=True) and not tag.get('aria-label') and not tag.get('value'):
                    # Skip empty elements unless they are inputs
                    if tag.name not in ['input', 'select', 'textarea']:
                        continue

                # Priority 1: ID
                if tag.get('id'):
                    valid_selectors.append(f"#{tag['id']}")
                    continue
                
                # Priority 2: Specific Classes (only if they look unique-ish)
                # This is risky, but better than nothing. LLM prefers IDs.
                # For now, let's stick mostly to IDs to be safe as per "Grounded" plan.
                # If we really need classes, we can add them, but let's filter strict.
                classes = tag.get('class', [])
                if classes:
                    # Filter out generic classes like "btn", "col-md-6"
                    meaningful_classes = [c for c in classes if c not in ['btn', 'container', 'row', 'col', 'd-flex']]
                    if meaningful_classes:
                        valid_selectors.append(f".{'.'.join(meaningful_classes)}")

            # Deduplicate
            valid_selectors = sorted(list(set(valid_selectors)))
            
            # [Context Protection] Limit to top 50 to prevent overflow
            if len(valid_selectors) > 50:
                # Heuristic: keep IDs over classes
                ids = [s for s in valid_selectors if s.startswith('#')]
                others = [s for s in valid_selectors if not s.startswith('#')]
                valid_selectors = ids[:50] + others[:(50 - len(ids))]
                valid_selectors = valid_selectors[:50]
                
            return valid_selectors

        except Exception as e:
            logger.warning(f"Failed to extract action space: {e}")
            return []

    def generate_golden_path(
        self, 
        task: Task, 
        architecture: Dict, 
        html_content: str, 
        logic_code: str
    ) -> Optional[Dict]:
        """
        Generates a sequence of actions to complete a task.
        """
        # Extract valid selectors
        valid_selectors = self._extract_valid_action_space(html_content)
        valid_selectors_str = json.dumps(valid_selectors, indent=2)

        prompt = PROMPT_GOLDEN_PATH_GENERATION.format(
            task_description=task.description,
            task_steps=json.dumps(getattr(task, 'steps', []), indent=2), # [Self-Correction 2.1] Multi-page Context
            architecture_json=json.dumps(architecture, indent=2),
            html_content=html_content[:5000], # Trucate if too large
            logic_code=logic_code[:2000],      # Focus on signatures
            task_id=task.id,
            valid_selectors=valid_selectors_str # [Self-Correction 2.0] Grounding
        )
        
        try:
            response = self.llm.prompt_json(prompt)
            if response and "steps" in response:
                return response
            return None
        except Exception as e:
            logger.error(f"Failed to generate golden path for {task.id}: {str(e)}")
            return None
