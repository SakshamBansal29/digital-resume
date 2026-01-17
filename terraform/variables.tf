variable "project_name" {
    description = "Name prefix for all resources"
    type        = string
    validation {
        condition     = can(regex("^[a-z0-9-]+$", var.project_name))
        error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
    }
}


variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, prod."
  }
}


variable "open_api_key" {
    description = "open API Key"
    type        = string
    sensitive = true
    validation {
        condition = length(var.open_api_key) > 1
        error_message = "Enter valid API Key"
    }
}

variable "ntfy_url" {
    description = "Notification URL"
    type        = string
    sensitive = true
    validation {
        condition = length(var.ntfy_url) > 1
        error_message = "NTFY URL not found or correct"
    }
}

variable "bedrock_model_id" {
  description = "Bedrock model ID"
  type        = string
  default     = "amazon.nova-micro-v1:0"
}


variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "api_throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 10
}

variable "api_throttle_rate_limit" {
  description = "API Gateway throttle rate limit"
  type        = number
  default     = 5
}

variable "use_custom_domain" {
  description = "Attach a custom domain to CloudFront"
  type        = bool
  default     = false
}

variable "root_domain" {
  description = "Apex domain name, e.g. mydomain.com"
  type        = string
  default     = ""
}