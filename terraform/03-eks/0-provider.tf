terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      # v5 required: the 4.x line predates EKS 1.31 and does not understand the
      # newer cluster API response fields.
      version = "~> 5.0"
    }
    # Used by 8-iam-oidc.tf to read the cluster's OIDC issuer certificate.
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  required_version = ">= 1.2.0"

  # Intentionally empty: bucket, key, region, and dynamodb_table are injected by
  # the CI workflow via `terraform init -backend-config=...`. Keeps the same code
  # usable against different state buckets per environment.
  # For local runs, see terraform/03-eks/README.md.
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}