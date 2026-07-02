# Remote state: S3 for storage, DynamoDB for locking.
# Values are supplied at init time so nothing account-specific lives in git:
#   terraform init -backend-config=backend.hcl
# See backend.hcl.example for the expected keys and the one-time bootstrap
# commands that create the bucket and lock table.
terraform {
  backend "s3" {}
}
