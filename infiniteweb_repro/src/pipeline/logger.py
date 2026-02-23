"""
Unified logging for the pipeline.
==================================
Provides consistent log formatting with emoji prefixes.
"""
import logging
from enum import Enum
from typing import Optional


class LogLevel(Enum):
    """Log level indicators with emoji prefixes."""
    PHASE = "🚀"
    STEP = "📋"
    SUCCESS = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    DEBUG = "🔍"
    INFO = "ℹ️"
    SAVE = "💾"


class PipelineLogger:
    """Unified logger for pipeline operations."""
    
    def __init__(self, name: str = "pipeline", verbose: bool = True):
        self.logger = logging.getLogger(name)
        self.verbose = verbose
        self._setup_handler()
    
    def _setup_handler(self):
        """Configure logging handler and formatter."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
    
    def phase(self, message: str):
        """Log a major phase start."""
        self.logger.info(f"\n{LogLevel.PHASE.value} [PHASE] {message}")
    
    def step(self, message: str):
        """Log a step within a phase."""
        self.logger.info(f"{LogLevel.STEP.value} {message}")
    
    def success(self, message: str):
        """Log a success message."""
        self.logger.info(f"{LogLevel.SUCCESS.value} {message}")
    
    def warning(self, message: str):
        """Log a warning message."""
        self.logger.warning(f"{LogLevel.WARNING.value} {message}")
    
    def error(self, message: str):
        """Log an error message."""
        self.logger.error(f"{LogLevel.ERROR.value} {message}")
    
    def debug(self, message: str):
        """Log a debug message (only if verbose)."""
        if self.verbose:
            self.logger.debug(f"{LogLevel.DEBUG.value} [DEBUG] {message}")
    
    def info(self, message: str):
        """Log an info message."""
        self.logger.info(f"{LogLevel.INFO.value} {message}")
    
    def save(self, filename: str):
        """Log a file save operation."""
        self.logger.info(f"{LogLevel.SAVE.value} Saved: {filename}")
