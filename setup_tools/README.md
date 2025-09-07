# Setup Tools

A modular Python framework for managing Salesforce and AWS operations in the SoCal Dreamin 2025 AWS demo project.

## Features

- **Modular Design**: Separate modules for AWS operations, Salesforce operations, and shared utilities
- **Command Pattern**: Each script implemented as a command class with consistent interface
- **Factory Pattern**: For creating different types of operations (AWS, Salesforce, etc.)
- **Configuration Management**: Centralized config handling with environment-specific overrides
- **Error Handling**: Comprehensive exception handling with meaningful error messages
- **Logging**: Structured logging with different levels and optional file output
- **CLI Interface**: Rich command-line interface with Click
- **Type Safety**: Full type hints throughout the codebase
- **Testing**: Comprehensive unit tests with pytest

## Installation

### Prerequisites

- Python 3.8 or higher
- Salesforce CLI (sf)
- OpenSSL (for certificate generation)
- SSH keygen (for AWS key generation)

### Virtual Environment Setup
```bash
# From the setup_tools directory
pip install -e setup_tools/python3 -m venv .venv
source setup_tools/.venv/bin/activate
# From the root directory (socal-dreamin-2025-aws)
cd socal-dreamin-2025-aws
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Development Installation

```bash
pip install -e .[dev]
```

## Usage

### Basic Commands

```bash
# List all available commands
python -m setup_tools list-commands

# Get detailed information about a command
python -m setup_tools command-info salesforce:create-scratch-org

# Salesforce operations
python -m setup_tools salesforce setup-complete --contact-email your-email@example.com --environment demo
python -m setup_tools salesforce create-scratch-org --org-name demo --duration-days 7
python -m setup_tools salesforce generate-certificate
python -m setup_tools salesforce setup-connected-app --contact-email your-email@example.com
python -m setup_tools salesforce create-integration-user --contact-email your-email@example.com
python -m setup_tools salesforce query-login-history

# AWS operations
python -m setup_tools aws generate-certificate --key-name my-key

# Infrastructure operations
python -m setup_tools infrastructure setup-terraform-vars --environment demo
python -m setup_tools infrastructure deploy-complete-lab --environment demo --validate
```

### Recommended Workflow

For a complete setup, follow this sequence:

1. **Complete Salesforce Setup** (one command):
   ```bash
   python -m setup_tools salesforce setup-complete --contact-email your-email@example.com --environment demo
   ```

2. **Setup Terraform Variables**:
   ```bash
   python -m setup_tools infrastructure setup-terraform-vars --environment demo
   ```

3. **Deploy Infrastructure**:
   ```bash
   python -m setup_tools infrastructure deploy-complete-lab --environment demo --validate
   ```

### Individual Commands

If you prefer to run commands individually:

1. **Generate Salesforce Certificate**:
   ```bash
   python -m setup_tools salesforce generate-certificate
   ```

2. **Create Scratch Org**:
   ```bash
   python -m setup_tools salesforce create-scratch-org --org-name demo --duration-days 30
   ```

3. **Setup Connected App**:
   ```bash
   python -m setup_tools salesforce setup-connected-app --contact-email your-email@example.com
   ```

4. **Create Integration User**:
   ```bash
   python -m setup_tools salesforce create-integration-user --contact-email your-email@example.com
   ```

5. **Setup Terraform Variables**:
   ```bash
   python -m setup_tools infrastructure setup-terraform-vars --environment demo
   ```

### Configuration

#### Using Configuration Files

```bash
# Use default configuration
python -m setup_tools salesforce create-scratch-org

# Use custom configuration file
python -m setup_tools --config config/demo.yaml salesforce create-scratch-org
```

#### Environment Variables

```bash
# Override configuration with environment variables
export SETUP_TOOLS_LOG_LEVEL=DEBUG
export SF_CONTACT_EMAIL=your@email.com
export AWS_REGION=us-east-1

python -m setup_tools salesforce create-scratch-org
```

#### Configuration File Format

```yaml
# config/demo.yaml
log_level: INFO
dry_run: false
verbose: true

salesforce:
  org_name: "demo-scratch-org"
  duration_days: 7
  contact_email: "demo@socaldreamin.com"

aws:
  region: "us-west-2"
  ssh_key_name: "demo-ec2-key"
  ec2_instance_type: "t3.small"
```

### Command Options

#### Global Options

- `--config, -c`: Configuration file path
- `--dry-run`: Preview operations without executing
- `--verbose, -v`: Enable verbose output
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR)

#### Salesforce Commands

**setup-complete**
- `--contact-email`: Contact email for Salesforce components
- `--environment`: Environment name (default: demo)

**create-scratch-org**
- `--org-name`: Name for the scratch org
- `--duration-days`: Duration in days (1-30)

**generate-certificate**
- No additional options

**setup-connected-app**
- `--contact-email`: Contact email for the Connected App
- `--environment`: Environment name for org targeting

**create-integration-user**
- `--contact-email`: Contact email for the integration user

**query-login-history**
- No additional options

#### AWS Commands

**generate-certificate**
- `--key-name`: Name for the SSH key

#### Infrastructure Commands

**setup-terraform-vars**
- `--environment`: Environment name (default: demo)

**deploy-complete-lab**
- `--environment`: Environment name (default: demo)
- `--validate`: Validate configuration before deployment

## Architecture

### Directory Structure

```
setup_tools/
├── __init__.py
├── main.py                 # CLI entry point
├── commands/
│   ├── __init__.py
│   ├── base.py            # Abstract base command
│   ├── salesforce/
│   │   ├── __init__.py
│   │   ├── create_scratch_org.py
│   │   ├── generate_certificate.py
│   │   └── query_login_history.py
│   └── aws/
│       ├── __init__.py
│       └── generate_certificate.py
├── core/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── logger.py          # Logging setup
│   └── exceptions.py      # Custom exceptions
├── utils/
│   ├── __init__.py
│   ├── file_operations.py
│   ├── shell_executor.py  # For subprocess calls
│   └── validators.py
├── config/
│   ├── default.yaml
│   └── environments/
└── tests/
```

### Design Patterns

#### Command Pattern

Each operation is implemented as a command class inheriting from `BaseCommand`:

```python
@register_command("salesforce:create-scratch-org")
class CreateScratchOrgCommand(BaseCommand):
    def execute(self, **kwargs) -> Any:
        # Implementation here
        pass
    
    def validate_inputs(self, **kwargs) -> None:
        # Validation here
        pass
```

#### Factory Pattern

Commands are created using the `CommandFactory`:

```python
command = CommandFactory.create_command(
    'salesforce:create-scratch-org',
    config,
    dry_run=False,
    verbose=True
)
```

#### Configuration Management

Configuration is loaded from multiple sources with precedence:

1. Default values
2. YAML configuration files
3. Environment variables
4. CLI arguments

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=setup_tools --cov-report=html

# Run specific test file
pytest tests/test_validators.py
```

### Code Quality

```bash
# Format code
black setup_tools/

# Lint code
flake8 setup_tools/

# Type checking
mypy setup_tools/
```

### Adding New Commands

1. Create a new command class inheriting from `BaseCommand`
2. Implement `execute()` and `validate_inputs()` methods
3. Register the command using `@register_command` decorator
4. Add CLI command in `main.py`
5. Write tests for the new command

Example:

```python
@register_command("my:new-command")
class MyNewCommand(BaseCommand):
    def execute(self, **kwargs) -> Any:
        # Implementation
        pass
    
    def validate_inputs(self, **kwargs) -> None:
        # Validation
        pass
```

## Error Handling

The framework provides comprehensive error handling with custom exceptions:

- `SetupToolsError`: Base exception for all framework errors
- `ConfigurationError`: Configuration-related errors
- `CommandError`: Command execution errors
- `ValidationError`: Input validation errors
- `SalesforceError`: Salesforce operation errors
- `AWSError`: AWS operation errors
- `CertificateError`: Certificate generation errors
- `FileOperationError`: File operation errors
- `ShellExecutionError`: Shell command execution errors

## Logging

The framework uses structured logging with Rich formatting:

```python
from setup_tools.core.logger import get_logger

logger = get_logger()
logger.info("Operation completed successfully")
logger.error("Operation failed: %s", error_message)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:

- Create an issue on GitHub
- Contact the SoCal Dreamin 2025 AWS team
- Check the documentation in the `docs/` directory
