"""
Base command class and factory pattern implementation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, Any, Optional
from pathlib import Path
import logging

from ..core.config import ProjectConfig
from ..core.exceptions import CommandError
from ..utils.shell_executor import ShellExecutor
from ..utils.file_operations import FileOperations
from ..utils.validators import Validators


class BaseCommand(ABC):
    """Abstract base class for all commands."""
    
    def __init__(self, config: ProjectConfig, dry_run: bool = False, verbose: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.verbose = verbose
        self.logger = logging.getLogger(f'setup_tools.{self.__class__.__name__}')
        self.shell = ShellExecutor(dry_run=dry_run, verbose=verbose)
        self.file_ops = FileOperations()
        self.validators = Validators()
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the command.
        
        Args:
            **kwargs: Command-specific arguments
            
        Returns:
            Command result
            
        Raises:
            CommandError: If command execution fails
        """
        pass
    
    @abstractmethod
    def validate_inputs(self, **kwargs) -> None:
        """
        Validate command inputs.
        
        Args:
            **kwargs: Command-specific arguments
            
        Raises:
            ValidationError: If inputs are invalid
        """
        pass
    
    def get_description(self) -> str:
        """Get command description."""
        return self.__class__.__doc__ or "No description available"
    
    def get_required_args(self) -> list:
        """Get list of required arguments."""
        return []
    
    def get_optional_args(self) -> dict:
        """Get dictionary of optional arguments with defaults."""
        return {}


class CommandFactory:
    """Factory for creating command instances."""
    
    _commands: Dict[str, Type[BaseCommand]] = {}
    
    @classmethod
    def register_command(cls, name: str, command_class: Type[BaseCommand]) -> None:
        """
        Register a command class.
        
        Args:
            name: Command name
            command_class: Command class
        """
        cls._commands[name] = command_class
    
    @classmethod
    def create_command(
        cls,
        name: str,
        config: ProjectConfig,
        dry_run: bool = False,
        verbose: bool = False
    ) -> BaseCommand:
        """
        Create a command instance.
        
        Args:
            name: Command name
            config: Project configuration
            dry_run: Whether to run in dry-run mode
            verbose: Whether to run in verbose mode
            
        Returns:
            Command instance
            
        Raises:
            CommandError: If command is not registered
        """
        if name not in cls._commands:
            available_commands = ', '.join(cls._commands.keys())
            raise CommandError(f"Unknown command: {name}. Available commands: {available_commands}")
        
        command_class = cls._commands[name]
        return command_class(config, dry_run=dry_run, verbose=verbose)
    
    @classmethod
    def list_commands(cls) -> Dict[str, str]:
        """
        List all registered commands with descriptions.
        
        Returns:
            Dictionary of command names and descriptions
        """
        commands = {}
        for name, command_class in cls._commands.items():
            # Create a temporary instance to get description
            temp_instance = command_class(None, dry_run=True, verbose=False)
            commands[name] = temp_instance.get_description()
        return commands
    
    @classmethod
    def get_command_info(cls, name: str) -> Dict[str, Any]:
        """
        Get detailed information about a command.
        
        Args:
            name: Command name
            
        Returns:
            Dictionary with command information
            
        Raises:
            CommandError: If command is not registered
        """
        if name not in cls._commands:
            raise CommandError(f"Unknown command: {name}")
        
        command_class = cls._commands[name]
        temp_instance = command_class(None, dry_run=True, verbose=False)
        
        return {
            'name': name,
            'description': temp_instance.get_description(),
            'required_args': temp_instance.get_required_args(),
            'optional_args': temp_instance.get_optional_args(),
            'class': command_class
        }


def register_command(name: str):
    """Decorator to register a command class."""
    def decorator(command_class: Type[BaseCommand]) -> Type[BaseCommand]:
        CommandFactory.register_command(name, command_class)
        return command_class
    return decorator
