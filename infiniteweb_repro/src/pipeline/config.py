"""
Pipeline configuration constants.
================================
Centralizes all magic numbers, file names, and limits.
"""
from dataclasses import dataclass


class FileNames:
    """Standard file names for generated artifacts."""
    LOGIC = "logic.js"
    EVALUATOR = "evaluator.js"
    TASKS = "tasks.json"
    BACKEND_TESTS = "backend_tests.js"
    STYLES = "styles.css"


class IntermediateFiles:
    """Intermediate file names with consistent numbering."""
    TASKS = "01_tasks.json"
    INITIAL_ARCH = "02_initial_architecture.json"
    INTERFACES = "03_interfaces.json"
    FINAL_ARCH = "04_final_architecture.json"
    DESIGN_ANALYSIS = "05_design_analysis.json"
    GENERATED_DATA = "06_generated_data.json"
    INITIAL_LOGIC = "07_initial_logic.js"
    INSTRUMENTATION = "08_instrumentation.json"
    FRAMEWORK = "09_framework.json"
    PAGE_DESIGNS = "05_page_designs.json"


class Limits:
    """Pipeline limits and thresholds."""
    MAX_CONCURRENCY = 1
    MAX_FIX_RETRIES = 3
    MAX_SELECTORS = 50
    HTML_TRUNCATE_LENGTH = 8000
    LOGIC_TRUNCATE_LENGTH = 4000
    TASK_COUNT_MIN = 3
    TASK_COUNT_MAX = 6


@dataclass
class PipelineConfig:
    """Runtime configuration for the pipeline."""
    max_concurrency: int = Limits.MAX_CONCURRENCY
    max_fix_retries: int = Limits.MAX_FIX_RETRIES
    max_selectors: int = Limits.MAX_SELECTORS
    html_truncate_length: int = Limits.HTML_TRUNCATE_LENGTH
    logic_truncate_length: int = Limits.LOGIC_TRUNCATE_LENGTH
    task_count_min: int = Limits.TASK_COUNT_MIN
    task_count_max: int = Limits.TASK_COUNT_MAX
    enable_visual_validation: bool = True
    enable_golden_path: bool = True
    enable_instrumentation: bool = True
    verbose: bool = True
