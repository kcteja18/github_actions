variable "project" {
  description = "Short project identifier used in resource names."
  type        = string
  default     = "vijay"

  validation {
    condition     = length(trimspace(var.project)) > 0
    error_message = "project must not be empty."
  }
}

variable "environment" {
  description = "Deployment environment name used in resource names."
  type        = string
  default     = "dev"

  validation {
    condition     = length(trimspace(var.environment)) > 0
    error_message = "environment must not be empty."
  }
}

variable "cluster_name" {
  description = "Name of the EKS cluster. Must match EKS_CLUSTER in .github/workflows/05-build-deploy.yaml."
  type        = string
  default     = "ness-itbot-eks"
  nullable    = false

  validation {
    condition     = length(trimspace(var.cluster_name)) > 0
    error_message = "cluster_name must not be empty."
  }
}

variable "kubernetes_version" {
  description = <<-EOT
    EKS control plane version. Keep the kubectl version in
    .github/workflows/05-build-deploy.yaml within one minor release of this.
  EOT
  type        = string
  default     = "1.31"
}

variable "aws_region" {
  description = "AWS region for the deployment."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = length(trimspace(var.aws_region)) > 0
    error_message = "aws_region must not be empty."
  }
}

variable "create_vpc" {
  description = "Whether to create a new VPC. Set to false to use an existing VPC via vpc_id."
  type        = bool
  default     = true
}

variable "vpc_id" {
  description = "Existing VPC ID to use when create_vpc is false. Ignored when create_vpc is true."
  type        = string
  default     = ""

  validation {
    condition     = var.create_vpc || length(trimspace(var.vpc_id)) > 0
    error_message = "Set create_vpc=true to create a new VPC or provide vpc_id to reuse an existing one."
  }
}

variable "internet_gateway_id" {
  description = "Existing internet gateway ID to use when create_vpc is false and the VPC already has one."
  type        = string
  default     = ""
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the private subnets. Provide exactly two CIDRs when creating subnets."
  type        = list(string)
  default     = ["10.0.128.0/19", "10.0.160.0/19"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets. Provide exactly two CIDRs when creating subnets."
  type        = list(string)
  default     = ["10.0.192.0/19", "10.0.224.0/19"]
}

variable "enable_nat_gateway" {
  description = <<-EOT
    Whether to create a NAT gateway and EIP for the private subnets.
    Worker nodes run in the PUBLIC subnets (see 7-nodes.tf), so no NAT is needed
    for the cluster to function and this stays false to avoid ~$32/month.
    Set to true only if you move nodes back to the private subnets or run other
    private-subnet workloads that need outbound internet.
  EOT
  type        = bool
  default     = false
}

variable "node_desired_size" {
  description = "Desired number of worker nodes in the EKS node group."
  type        = number
  default     = 1

  validation {
    condition     = var.node_desired_size >= 0
    error_message = "node_desired_size must be greater than or equal to 0."
  }
}

variable "node_min_size" {
  description = "Minimum number of worker nodes in the EKS node group."
  type        = number
  default     = 1

  validation {
    condition     = var.node_min_size >= 0
    error_message = "node_min_size must be greater than or equal to 0."
  }
}

variable "node_max_size" {
  description = "Maximum number of worker nodes in the EKS node group."
  type        = number
  default     = 2

  validation {
    condition     = var.node_max_size >= 1
    error_message = "node_max_size must be greater than or equal to 1."
  }
}

variable "instance_types" {
  description = "List of instance types for the EKS managed node group."
  type        = list(string)
  default     = ["t3.small"]
}

variable "capacity_type" {
  description = "Capacity type for the managed node group."
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.capacity_type)
    error_message = "capacity_type must be either ON_DEMAND or SPOT."
  }
}

locals {
  name_prefix = "${var.project}-${var.environment}"

  vpc_name                 = "${local.name_prefix}-vpc"
  igw_name                 = "${local.name_prefix}-igw"
  private_route_table_name = "${local.name_prefix}-private-rt"
  public_route_table_name  = "${local.name_prefix}-public-rt"
  nat_eip_name             = "${local.name_prefix}-nat-eip"
  nat_gateway_name         = "${local.name_prefix}-nat"

  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "Terraform"
    ClusterName = var.cluster_name
  }
}
