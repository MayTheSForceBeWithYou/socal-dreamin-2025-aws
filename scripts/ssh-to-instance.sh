#!/bin/bash

# Get EC2 instance IP from Terraform output
EC2_IP=$(cd aws/terraform && terraform output -raw ec2_public_ip 2>/dev/null)

if [ -z "$EC2_IP" ]; then
    echo "Error: Could not get EC2 instance IP from Terraform output"
    echo "Make sure the infrastructure is deployed and terraform.tfstate exists"
    exit 1
fi

# If a command is provided, execute it on the instance
if [ $# -eq 0 ]; then
    echo "SSH to EC2 instance: $EC2_IP"
    ssh -i ../aws/certs/aws-ec2 -o StrictHostKeyChecking=no ec2-user@$EC2_IP
else
    echo "Executing command on EC2 instance: $EC2_IP"
    ssh -i ../aws/certs/aws-ec2 -o StrictHostKeyChecking=no ec2-user@$EC2_IP "$@"
fi
