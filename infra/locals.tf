locals {
  name = "${var.project_name}-${var.environment}"

  # Two AZs keeps the footprint minimal while still satisfying EKS and RDS
  # subnet group requirements.
  az_count = 2
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}
