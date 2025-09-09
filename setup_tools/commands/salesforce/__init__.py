"""
Salesforce command modules.
"""

# Import all Salesforce commands to register them
from .create_integration_user import CreateIntegrationUserCommand
from .create_scratch_org import CreateScratchOrgCommand
from .deploy_permission_sets import DeployPermissionSetsCommand
from .deploy_project import DeployProjectCommand
from .generate_certificate import GenerateSalesforceCertificateCommand
from .query_login_history import QueryLoginHistoryCommand
from .setup_complete import SetupCompleteSalesforceCommand
from .setup_connected_app import SetupConnectedAppCommand

__all__ = [
    'CreateIntegrationUserCommand',
    'CreateScratchOrgCommand',
    'DeployPermissionSetsCommand',
    'DeployProjectCommand',
    'GenerateSalesforceCertificateCommand',
    'QueryLoginHistoryCommand',
    'SetupCompleteSalesforceCommand',
    'SetupConnectedAppCommand'
]
