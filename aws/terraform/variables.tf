variable "region" {
  description = "AWS region for resources"
  type        = string
}

variable "bucket_prefix" {
  description = "Shared, lowercase, DNS-safe prefix"
  type        = string
}

variable "environment" {
  description = "Environment tag (e.g., lab, demo, dev)"
  type        = string
}

variable "owner_suffix" {
  description = "Attendee-specific suffix (e.g., flastname, astro)"
  type        = string

  # Keep names S3-legal and predictable in a workshop
  validation {
    condition     = can(regex("^[a-z0-9-]{2,32}$", var.owner_suffix))
    error_message = "owner_suffix must be 2-32 chars, lowercase letters, digits, or hyphens."
  }
}

variable "user_name" {
  description = "IAM user name Salesforce will use for SigV4"
  type        = string
  default     = "sfdc-event-relay-user"
}

variable "policy_name" {
  description = "Name for the least-privilege policy"
  type        = string
  default     = "sfdc-event-relay-put-partner-events"
}
