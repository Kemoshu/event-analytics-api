output "aws_region" {
  description = "Region everything is deployed in"
  value       = var.aws_region
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "ecr_repository_url" {
  description = "ECR repository for the API image"
  value       = aws_ecr_repository.api.repository_url
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.endpoint
}

output "rds_master_secret_arn" {
  description = "Secrets Manager ARN holding the RDS master credentials"
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}

output "github_actions_role_arn" {
  description = "IAM role CI assumes via OIDC; set as AWS_DEPLOY_ROLE_ARN repo variable"
  value       = aws_iam_role.github_actions.arn
}

output "kubeconfig_command" {
  description = "Command to configure kubectl against the cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.main.name}"
}
