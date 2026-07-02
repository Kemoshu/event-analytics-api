variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "event-analytics"
}

variable "environment" {
  description = "Environment tag (demo, staging, prod)"
  type        = string
  default     = "demo"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "kubernetes_version" {
  description = "EKS control plane version"
  type        = string
  default     = "1.31"
}

variable "node_instance_types" {
  description = "Instance types for the managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Desired node count"
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum node count"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum node count"
  type        = number
  default     = 3
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_engine_version" {
  description = "PostgreSQL major version for RDS"
  type        = string
  default     = "16"
}

variable "db_name" {
  description = "Initial database name"
  type        = string
  default     = "events"
}

variable "db_username" {
  description = "Master username for RDS"
  type        = string
  default     = "app"
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the deploy role, in owner/name form"
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "Must be in owner/name form, e.g. ramosk-dev/event-analytics-api."
  }
}

variable "app_namespace" {
  description = "Kubernetes namespace the CI role may deploy into"
  type        = string
  default     = "event-analytics"
}
