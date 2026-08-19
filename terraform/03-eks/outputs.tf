output "cluster_name" {
  description = "The name of the EKS cluster."
  value       = aws_eks_cluster.demo.name
}

output "cluster_endpoint" {
  description = "The endpoint for the EKS cluster API server."
  value       = aws_eks_cluster.demo.endpoint
}

output "vpc_id" {
  description = "The ID of the VPC."
  value       = local.vpc_id
}

output "private_subnet_ids" {
  description = "The IDs of the private subnets."
  value = [
    aws_subnet.private-us-east-1a.id,
    aws_subnet.private-us-east-1b.id
  ]
}

output "public_subnet_ids" {
  description = "The IDs of the public subnets."
  value = [
    aws_subnet.public-us-east-1a.id,
    aws_subnet.public-us-east-1b.id
  ]
}
