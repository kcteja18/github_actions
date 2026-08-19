# EKS Terraform configuration

This folder provisions a VPC, public/private subnets, an EKS cluster, and a managed node group with safer naming and cost controls.

## Required variables

- project: short identifier for resource names
- environment: deployment environment name
- cluster_name: EKS cluster name
- aws_region: target AWS region

## Optional variables

- enable_nat_gateway: set to false to skip NAT gateway and EIP creation (saves cost)
- node_desired_size: desired worker node count (default 1)
- node_min_size: minimum worker node count (default 1)
- node_max_size: maximum worker node count (default 2)
- instance_types: node group instance types (default ["t3.small"])
- capacity_type: ON_DEMAND or SPOT (default ON_DEMAND)

## Example dev tfvars

```hcl
project     = "demo"
environment = "dev"
cluster_name = "demo-dev"
aws_region  = "us-east-1"
node_desired_size = 1
node_min_size     = 1
node_max_size     = 2
instance_types   = ["t3.small"]
capacity_type    = "ON_DEMAND"
enable_nat_gateway = true
```

## NAT toggle note

Setting enable_nat_gateway to false avoids creating the NAT gateway and EIP, which lowers ongoing cost but removes outbound internet access from private subnets unless you provide another route path.
