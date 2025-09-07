"""
Logging configuration for the setup tools framework.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler


class SetupToolsLogger:
    """Centralized logging configuration."""
    
    _instance: Optional['SetupToolsLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls) -> 'SetupToolsLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Set up the logger with Rich formatting."""
        self._logger = logging.getLogger('setup_tools')
        self._logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)
        
        # Create Rich console for colored output
        console = Console(stderr=True)
        
        # Create Rich handler
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True
        )
        
        # Set format
        formatter = logging.Formatter(
            fmt="%(message)s",
            datefmt="[%X]"
        )
        rich_handler.setFormatter(formatter)
        
        self._logger.addHandler(rich_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self._logger
    
    def set_level(self, level: str) -> None:
        """Set the logging level."""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_map:
            self._logger.setLevel(level_map[level.upper()])
        else:
            raise ValueError(f"Invalid log level: {level}")
    
    def add_file_handler(self, log_file: Path) -> None:
        """Add file logging handler."""
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        self._logger.addHandler(file_handler)


def get_logger() -> logging.Logger:
    """Get the global logger instance."""
    return SetupToolsLogger().get_logger()
