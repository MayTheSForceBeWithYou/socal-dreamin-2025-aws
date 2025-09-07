"""
Custom exceptions for the setup tools framework.
"""

from typing import Optional


class SetupToolsError(Exception):
    """Base exception for all setup tools errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class ConfigurationError(SetupToolsError):
    """Raised when there's a configuration-related error."""
    pass


class CommandError(SetupToolsError):
    """Raised when a command execution fails."""
    pass


class ValidationError(SetupToolsError):
    """Raised when input validation fails."""
    pass


class SalesforceError(SetupToolsError):
    """Raised when Salesforce operations fail."""
    pass


class AWSError(SetupToolsError):
    """Raised when AWS operations fail."""
    pass


class TerraformError(SetupToolsError):
    """Raised when Terraform operations fail."""
    pass


class CertificateError(SetupToolsError):
    """Raised when certificate generation or management fails."""
    pass


class FileOperationError(SetupToolsError):
    """Raised when file operations fail."""
    pass


class ShellExecutionError(SetupToolsError):
    """Raised when shell command execution fails."""
    pass
