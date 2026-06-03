variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for deployment"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (development/staging/production)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "bq_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}

variable "service_account_email" {
  description = "Service account email for Cloud Run and BigQuery"
  type        = string
}

variable "frontend_domain" {
  description = "Frontend domain for CORS configuration"
  type        = string
  default     = "*.run.app"
}

variable "min_backend_instances" {
  description = "Minimum Cloud Run instances for backend"
  type        = number
  default     = 1
}

variable "max_backend_instances" {
  description = "Maximum Cloud Run instances for backend"
  type        = number
  default     = 10
}
