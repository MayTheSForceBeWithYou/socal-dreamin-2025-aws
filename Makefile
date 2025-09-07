.PHONY: help deploy ssh logs clean

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

deploy: ## Deploy the lab environment
	@./scripts/deploy.sh

ssh: ## SSH to the EC2 instance
	@./scripts/ssh-to-instance.sh

logs: ## View application logs
	@./scripts/ssh-to-instance.sh "sudo journalctl -u salesforce-streamer -f"

clean: ## Destroy the environment
	@cd aws/terraform && terraform destroy -var-file="terraform.tfvars"

status: ## Check service status
	@./scripts/ssh-to-instance.sh "sudo systemctl status salesforce-streamer"

restart: ## Restart the service
	@./scripts/ssh-to-instance.sh "sudo systemctl restart salesforce-streamer"

init: ## Initialize Terraform
	@cd aws/terraform && terraform init

plan: ## Plan Terraform changes
	@cd aws/terraform && terraform plan -var-file="terraform.tfvars"

apply: ## Apply Terraform changes
	@cd aws/terraform && terraform apply -var-file="terraform.tfvars"

validate: ## Validate Terraform configuration
	@cd aws/terraform && terraform validate

fmt: ## Format Terraform files
	@cd aws/terraform && terraform fmt -recursive
