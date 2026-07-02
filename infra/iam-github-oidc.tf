# Federated identity for GitHub Actions: CI assumes a short-lived role via
# OIDC, so no AWS access keys are stored as repository secrets.

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

data "aws_iam_policy_document" "github_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Only version tags on this repository may deploy.
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:ref:refs/tags/v*"]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name                 = "${local.name}-github-actions"
  assume_role_policy   = data.aws_iam_policy_document.github_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "github_actions" {
  statement {
    sid       = "EcrAuth"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "EcrPushPull"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
    ]
    resources = [aws_ecr_repository.api.arn]
  }

  statement {
    sid       = "EksDescribe"
    effect    = "Allow"
    actions   = ["eks:DescribeCluster"]
    resources = [aws_eks_cluster.main.arn]
  }
}

resource "aws_iam_role_policy" "github_actions" {
  name   = "deploy"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.github_actions.json
}

# Kubernetes-side permissions: edit access scoped to the app namespace,
# granted through EKS access entries rather than the aws-auth ConfigMap.
resource "aws_eks_access_entry" "github_actions" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_iam_role.github_actions.arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "github_actions" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_iam_role.github_actions.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"

  access_scope {
    type       = "namespace"
    namespaces = [var.app_namespace]
  }

  depends_on = [aws_eks_access_entry.github_actions]
}
