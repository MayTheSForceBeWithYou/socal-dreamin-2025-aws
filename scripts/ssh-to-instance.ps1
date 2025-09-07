# PowerShell script to SSH to EC2 instance
# Usage: .\ssh-to-instance.ps1 [command]
# If no command is provided, opens an interactive SSH session
# If a command is provided, executes it on the remote instance

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Command
)

# Function to get EC2 instance IP from Terraform output
function Get-EC2IP {
    try {
        # Change to terraform directory and get the IP
        Push-Location "aws/terraform"
        $ip = terraform output -raw ec2_public_ip 2>$null
        
        if ([string]::IsNullOrWhiteSpace($ip)) {
            throw "No IP address returned from Terraform"
        }
        
        return $ip.Trim()
    }
    catch {
        Write-Error "Error: Could not get EC2 instance IP from Terraform output"
        Write-Error "Make sure the infrastructure is deployed and terraform.tfstate exists"
        exit 1
    }
    finally {
        Pop-Location
    }
}

# Function to check if SSH key exists
function Test-SSHKey {
    $sshKeyPath = "$env:USERPROFILE\.ssh\your-key.pem"
    if (-not (Test-Path $sshKeyPath)) {
        Write-Error "SSH key not found at: $sshKeyPath"
        Write-Error "Please ensure your SSH key is in the correct location"
        exit 1
    }
    return $sshKeyPath
}

# Main execution
try {
    # Get EC2 instance IP
    $ec2IP = Get-EC2IP
    
    # Check if SSH key exists
    $sshKeyPath = Test-SSHKey
    
    # Build SSH command
    $sshCommand = "ssh -i `"$sshKeyPath`" -o StrictHostKeyChecking=no ec2-user@$ec2IP"
    
    if ($Command.Count -eq 0) {
        # No command provided, open interactive SSH session
        Write-Host "SSH to EC2 instance: $ec2IP" -ForegroundColor Green
        Invoke-Expression $sshCommand
    }
    else {
        # Command provided, execute it on the remote instance
        $commandString = $Command -join " "
        Write-Host "Executing command on EC2 instance: $ec2IP" -ForegroundColor Green
        Write-Host "Command: $commandString" -ForegroundColor Yellow
        
        $fullCommand = "$sshCommand `"$commandString`""
        Invoke-Expression $fullCommand
    }
}
catch {
    Write-Error "An error occurred: $($_.Exception.Message)"
    exit 1
}
