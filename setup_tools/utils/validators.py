"""
Input validation utilities.
"""

import re
from pathlib import Path
from typing import Union, List, Optional
from urllib.parse import urlparse
from ..core.exceptions import ValidationError


class Validators:
    """Input validation utilities."""
    
    EMAIL_REGEX = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
    ORG_NAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    @staticmethod
    def validate_email(email: str) -> str:
        """
        Validate email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            Validated email address
            
        Raises:
            ValidationError: If email format is invalid
        """
        if not email or not isinstance(email, str):
            raise ValidationError("Email address is required")
        
        email = email.strip()
        
        if not Validators.EMAIL_REGEX.match(email):
            raise ValidationError(f"Invalid email format: {email}")
        
        return email
    
    @staticmethod
    def validate_org_name(org_name: str) -> str:
        """
        Validate Salesforce org name format.
        
        Args:
            org_name: Org name to validate
            
        Returns:
            Validated org name
            
        Raises:
            ValidationError: If org name format is invalid
        """
        if not org_name or not isinstance(org_name, str):
            raise ValidationError("Org name is required")
        
        org_name = org_name.strip()
        
        if not Validators.ORG_NAME_REGEX.match(org_name):
            raise ValidationError(f"Invalid org name format: {org_name}. Use only letters, numbers, hyphens, and underscores.")
        
        if len(org_name) < 3:
            raise ValidationError("Org name must be at least 3 characters long")
        
        if len(org_name) > 50:
            raise ValidationError("Org name must be no more than 50 characters long")
        
        return org_name
    
    @staticmethod
    def validate_duration_days(duration: Union[int, str]) -> int:
        """
        Validate scratch org duration in days.
        
        Args:
            duration: Duration in days
            
        Returns:
            Validated duration as integer
            
        Raises:
            ValidationError: If duration is invalid
        """
        try:
            duration = int(duration)
        except (ValueError, TypeError):
            raise ValidationError("Duration must be a valid integer")
        
        if duration < 1:
            raise ValidationError("Duration must be at least 1 day")
        
        if duration > 30:
            raise ValidationError("Duration cannot exceed 30 days")
        
        return duration
    
    @staticmethod
    def validate_file_path(path: Union[str, Path], must_exist: bool = True) -> Path:
        """
        Validate file path.
        
        Args:
            path: File path to validate
            must_exist: Whether file must exist
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If path is invalid
        """
        try:
            path = Path(path)
        except Exception as e:
            raise ValidationError(f"Invalid file path: {e}")
        
        if must_exist and not path.exists():
            raise ValidationError(f"File does not exist: {path}")
        
        return path
    
    @staticmethod
    def validate_directory_path(path: Union[str, Path], must_exist: bool = True) -> Path:
        """
        Validate directory path.
        
        Args:
            path: Directory path to validate
            must_exist: Whether directory must exist
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If path is invalid
        """
        try:
            path = Path(path)
        except Exception as e:
            raise ValidationError(f"Invalid directory path: {e}")
        
        if must_exist and not path.exists():
            raise ValidationError(f"Directory does not exist: {path}")
        
        if must_exist and not path.is_dir():
            raise ValidationError(f"Path is not a directory: {path}")
        
        return path
    
    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            Validated URL
            
        Raises:
            ValidationError: If URL format is invalid
        """
        if not url or not isinstance(url, str):
            raise ValidationError("URL is required")
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValidationError(f"Invalid URL format: {url}")
        except Exception as e:
            raise ValidationError(f"Invalid URL format: {e}")
        
        return url
    
    @staticmethod
    def validate_aws_region(region: str) -> str:
        """
        Validate AWS region format.
        
        Args:
            region: AWS region to validate
            
        Returns:
            Validated region
            
        Raises:
            ValidationError: If region format is invalid
        """
        if not region or not isinstance(region, str):
            raise ValidationError("AWS region is required")
        
        region = region.strip()
        
        # Basic AWS region format validation
        if not re.match(r'^[a-z]{2}-[a-z]+-\d+$', region):
            raise ValidationError(f"Invalid AWS region format: {region}")
        
        return region
    
    @staticmethod
    def validate_ssh_key_name(key_name: str) -> str:
        """
        Validate SSH key name format.
        
        Args:
            key_name: SSH key name to validate
            
        Returns:
            Validated key name
            
        Raises:
            ValidationError: If key name format is invalid
        """
        if not key_name or not isinstance(key_name, str):
            raise ValidationError("SSH key name is required")
        
        key_name = key_name.strip()
        
        # SSH key names should be alphanumeric with hyphens and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', key_name):
            raise ValidationError(f"Invalid SSH key name format: {key_name}")
        
        if len(key_name) < 1:
            raise ValidationError("SSH key name cannot be empty")
        
        if len(key_name) > 50:
            raise ValidationError("SSH key name must be no more than 50 characters")
        
        return key_name
    
    @staticmethod
    def validate_required_fields(data: dict, required_fields: List[str]) -> None:
        """
        Validate that required fields are present in data.
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
            
        Raises:
            ValidationError: If required fields are missing
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    @staticmethod
    def validate_choice(value: str, choices: List[str], field_name: str = "value") -> str:
        """
        Validate that a value is one of the allowed choices.
        
        Args:
            value: Value to validate
            choices: List of allowed choices
            field_name: Name of the field for error messages
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If value is not in choices
        """
        if not value or not isinstance(value, str):
            raise ValidationError(f"{field_name} is required")
        
        value = value.strip()
        
        if value not in choices:
            raise ValidationError(f"Invalid {field_name}: {value}. Must be one of: {', '.join(choices)}")
        
        return value
