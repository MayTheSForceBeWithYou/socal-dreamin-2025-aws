"""
Shell command execution utilities.
"""

import subprocess
import shlex
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from ..core.exceptions import ShellExecutionError


class ShellExecutor:
    """Handles shell command execution with proper error handling."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
    
    def execute(
        self,
        command: Union[str, List[str]],
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        check: bool = True,
        capture_output: bool = False,
        timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess:
        """
        Execute a shell command.
        
        Args:
            command: Command to execute (string or list)
            cwd: Working directory
            env: Environment variables
            check: Whether to raise exception on non-zero exit code
            capture_output: Whether to capture stdout/stderr
            timeout: Command timeout in seconds
            
        Returns:
            CompletedProcess object
            
        Raises:
            ShellExecutionError: If command fails and check=True
        """
        if self.dry_run:
            print(f"[DRY RUN] Would execute: {command}")
            if cwd:
                print(f"[DRY RUN] Working directory: {cwd}")
            return subprocess.CompletedProcess(
                args=command, returncode=0, stdout="", stderr=""
            )
        
        # Convert command to list if it's a string
        if isinstance(command, str):
            command = shlex.split(command)
        
        if self.verbose:
            print(f"Executing: {' '.join(command)}")
            if cwd:
                print(f"Working directory: {cwd}")
        
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                check=check,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            
            if self.verbose and result.stdout:
                print(f"STDOUT: {result.stdout}")
            if self.verbose and result.stderr:
                print(f"STDERR: {result.stderr}")
            
            return result
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed with exit code {e.returncode}: {' '.join(command)}"
            if e.stderr:
                error_msg += f"\nError output: {e.stderr}"
            raise ShellExecutionError(error_msg)
        
        except subprocess.TimeoutExpired as e:
            error_msg = f"Command timed out after {timeout} seconds: {' '.join(command)}"
            raise ShellExecutionError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error executing command {' '.join(command)}: {e}"
            raise ShellExecutionError(error_msg)
    
    def execute_interactive(
        self,
        command: Union[str, List[str]],
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Execute a command interactively (no output capture).
        
        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            
        Returns:
            Exit code
        """
        if self.dry_run:
            print(f"[DRY RUN] Would execute interactively: {command}")
            return 0
        
        if isinstance(command, str):
            command = shlex.split(command)
        
        if self.verbose:
            print(f"Executing interactively: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                check=False
            )
            return result.returncode
            
        except Exception as e:
            error_msg = f"Unexpected error executing interactive command {' '.join(command)}: {e}"
            raise ShellExecutionError(error_msg)
    
    def check_command_exists(self, command: str) -> bool:
        """
        Check if a command exists in the system PATH.
        
        Args:
            command: Command name to check
            
        Returns:
            True if command exists, False otherwise
        """
        try:
            self.execute(f"which {command}", capture_output=True, check=True)
            return True
        except ShellExecutionError:
            return False
    
    def get_command_output(
        self,
        command: Union[str, List[str]],
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Execute command and return stdout.
        
        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            
        Returns:
            Command stdout
            
        Raises:
            ShellExecutionError: If command fails
        """
        result = self.execute(command, cwd=cwd, env=env, capture_output=True, check=True)
        return result.stdout.strip()
