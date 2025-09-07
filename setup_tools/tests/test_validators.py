"""
Tests for validators module.
"""

import pytest
from pathlib import Path
from setup_tools.utils.validators import Validators
from setup_tools.core.exceptions import ValidationError


class TestValidators:
    """Test cases for Validators class."""
    
    def test_validate_email_valid(self):
        """Test valid email addresses."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com"
        ]
        
        for email in valid_emails:
            result = Validators.validate_email(email)
            assert result == email
    
    def test_validate_email_invalid(self):
        """Test invalid email addresses."""
        invalid_emails = [
            "",
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com",
            "user..name@example.com"
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                Validators.validate_email(email)
    
    def test_validate_org_name_valid(self):
        """Test valid org names."""
        valid_names = [
            "test-org",
            "test_org",
            "test123",
            "my-org-name",
            "org_name_123"
        ]
        
        for name in valid_names:
            result = Validators.validate_org_name(name)
            assert result == name
    
    def test_validate_org_name_invalid(self):
        """Test invalid org names."""
        invalid_names = [
            "",
            "test org",  # space
            "test.org",  # dot
            "test@org",  # @ symbol
            "a",  # too short
            "a" * 51,  # too long
            "test-org!",  # special character
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError):
                Validators.validate_org_name(name)
    
    def test_validate_duration_days_valid(self):
        """Test valid duration values."""
        valid_durations = [1, 7, 15, 30, "1", "7", "15", "30"]
        
        for duration in valid_durations:
            result = Validators.validate_duration_days(duration)
            assert isinstance(result, int)
            assert 1 <= result <= 30
    
    def test_validate_duration_days_invalid(self):
        """Test invalid duration values."""
        invalid_durations = [
            0, 31, -1, "0", "31", "invalid", None, ""
        ]
        
        for duration in invalid_durations:
            with pytest.raises(ValidationError):
                Validators.validate_duration_days(duration)
    
    def test_validate_aws_region_valid(self):
        """Test valid AWS regions."""
        valid_regions = [
            "us-west-2",
            "us-east-1",
            "eu-west-1",
            "ap-southeast-1"
        ]
        
        for region in valid_regions:
            result = Validators.validate_aws_region(region)
            assert result == region
    
    def test_validate_aws_region_invalid(self):
        """Test invalid AWS regions."""
        invalid_regions = [
            "",
            "invalid-region",
            "us-west-2-invalid",
            "US-WEST-2",  # uppercase
            "us_west_2",  # underscore
        ]
        
        for region in invalid_regions:
            with pytest.raises(ValidationError):
                Validators.validate_aws_region(region)
    
    def test_validate_ssh_key_name_valid(self):
        """Test valid SSH key names."""
        valid_names = [
            "my-key",
            "my_key",
            "key123",
            "my-key-name",
            "key_name_123"
        ]
        
        for name in valid_names:
            result = Validators.validate_ssh_key_name(name)
            assert result == name
    
    def test_validate_ssh_key_name_invalid(self):
        """Test invalid SSH key names."""
        invalid_names = [
            "",
            "my key",  # space
            "my.key",  # dot
            "my@key",  # @ symbol
            "a" * 51,  # too long
            "my-key!",  # special character
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError):
                Validators.validate_ssh_key_name(name)
    
    def test_validate_required_fields_valid(self):
        """Test valid required fields."""
        data = {
            "field1": "value1",
            "field2": "value2",
            "field3": "value3"
        }
        required_fields = ["field1", "field2"]
        
        # Should not raise exception
        Validators.validate_required_fields(data, required_fields)
    
    def test_validate_required_fields_invalid(self):
        """Test invalid required fields."""
        data = {
            "field1": "value1",
            "field2": "",  # empty
            "field3": "value3"
        }
        required_fields = ["field1", "field2", "field4"]  # field4 missing
        
        with pytest.raises(ValidationError) as exc_info:
            Validators.validate_required_fields(data, required_fields)
        
        assert "field2" in str(exc_info.value)
        assert "field4" in str(exc_info.value)
    
    def test_validate_choice_valid(self):
        """Test valid choice values."""
        choices = ["option1", "option2", "option3"]
        
        for choice in choices:
            result = Validators.validate_choice(choice, choices, "test_field")
            assert result == choice
    
    def test_validate_choice_invalid(self):
        """Test invalid choice values."""
        choices = ["option1", "option2", "option3"]
        invalid_values = ["option4", "invalid", ""]
        
        for value in invalid_values:
            with pytest.raises(ValidationError):
                Validators.validate_choice(value, choices, "test_field")
