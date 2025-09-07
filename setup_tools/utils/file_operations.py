"""
File operation utilities.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import re
from ..core.exceptions import FileOperationError


class FileOperations:
    """Handles file operations with proper error handling."""
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Directory path
            
        Returns:
            Path object of the directory
            
        Raises:
            FileOperationError: If directory creation fails
        """
        try:
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception as e:
            raise FileOperationError(f"Failed to create directory {path}: {e}")
    
    @staticmethod
    def copy_file(
        src: Union[str, Path],
        dst: Union[str, Path],
        backup: bool = False
    ) -> None:
        """
        Copy a file from source to destination.
        
        Args:
            src: Source file path
            dst: Destination file path
            backup: Whether to create backup if destination exists
            
        Raises:
            FileOperationError: If copy operation fails
        """
        try:
            src = Path(src)
            dst = Path(dst)
            
            if not src.exists():
                raise FileOperationError(f"Source file does not exist: {src}")
            
            # Create backup if requested and destination exists
            if backup and dst.exists():
                backup_path = dst.with_suffix(dst.suffix + '.bak')
                shutil.copy2(dst, backup_path)
            
            # Ensure destination directory exists
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(src, dst)
            
        except Exception as e:
            raise FileOperationError(f"Failed to copy file from {src} to {dst}: {e}")
    
    @staticmethod
    def read_file(path: Union[str, Path]) -> str:
        """
        Read contents of a file.
        
        Args:
            path: File path
            
        Returns:
            File contents as string
            
        Raises:
            FileOperationError: If file read fails
        """
        try:
            path = Path(path)
            if not path.exists():
                raise FileOperationError(f"File does not exist: {path}")
            
            return path.read_text(encoding='utf-8')
            
        except Exception as e:
            raise FileOperationError(f"Failed to read file {path}: {e}")
    
    @staticmethod
    def write_file(
        path: Union[str, Path],
        content: str,
        backup: bool = False
    ) -> None:
        """
        Write content to a file.
        
        Args:
            path: File path
            content: Content to write
            backup: Whether to create backup if file exists
            
        Raises:
            FileOperationError: If file write fails
        """
        try:
            path = Path(path)
            
            # Create backup if requested and file exists
            if backup and path.exists():
                backup_path = path.with_suffix(path.suffix + '.bak')
                shutil.copy2(path, backup_path)
            
            # Ensure directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            path.write_text(content, encoding='utf-8')
            
        except Exception as e:
            raise FileOperationError(f"Failed to write file {path}: {e}")
    
    @staticmethod
    def replace_in_file(
        path: Union[str, Path],
        replacements: Dict[str, str],
        backup: bool = True
    ) -> None:
        """
        Replace text in a file using regex patterns.
        
        Args:
            path: File path
            replacements: Dictionary of pattern -> replacement
            backup: Whether to create backup
            
        Raises:
            FileOperationError: If replacement fails
        """
        try:
            path = Path(path)
            
            if not path.exists():
                raise FileOperationError(f"File does not exist: {path}")
            
            # Read file content
            content = path.read_text(encoding='utf-8')
            
            # Create backup if requested
            if backup:
                backup_path = path.with_suffix(path.suffix + '.bak')
                shutil.copy2(path, backup_path)
            
            # Apply replacements
            for pattern, replacement in replacements.items():
                content = re.sub(pattern, replacement, content)
            
            # Write updated content
            path.write_text(content, encoding='utf-8')
            
        except Exception as e:
            raise FileOperationError(f"Failed to replace text in file {path}: {e}")
    
    @staticmethod
    def find_files(
        directory: Union[str, Path],
        pattern: str,
        recursive: bool = True
    ) -> List[Path]:
        """
        Find files matching a pattern.
        
        Args:
            directory: Directory to search
            pattern: File pattern (glob)
            recursive: Whether to search recursively
            
        Returns:
            List of matching file paths
            
        Raises:
            FileOperationError: If search fails
        """
        try:
            directory = Path(directory)
            
            if not directory.exists():
                raise FileOperationError(f"Directory does not exist: {directory}")
            
            if recursive:
                return list(directory.rglob(pattern))
            else:
                return list(directory.glob(pattern))
                
        except Exception as e:
            raise FileOperationError(f"Failed to find files in {directory}: {e}")
    
    @staticmethod
    def create_temp_file(
        content: str,
        suffix: str = ".tmp",
        prefix: str = "setup_tools_"
    ) -> Path:
        """
        Create a temporary file with content.
        
        Args:
            content: File content
            suffix: File suffix
            prefix: File prefix
            
        Returns:
            Path to temporary file
            
        Raises:
            FileOperationError: If temp file creation fails
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=suffix,
                prefix=prefix,
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(content)
                return Path(f.name)
                
        except Exception as e:
            raise FileOperationError(f"Failed to create temporary file: {e}")
    
    @staticmethod
    def cleanup_temp_file(path: Union[str, Path]) -> None:
        """
        Clean up a temporary file.
        
        Args:
            path: Path to temporary file
            
        Raises:
            FileOperationError: If cleanup fails
        """
        try:
            path = Path(path)
            if path.exists():
                path.unlink()
        except Exception as e:
            raise FileOperationError(f"Failed to cleanup temporary file {path}: {e}")
