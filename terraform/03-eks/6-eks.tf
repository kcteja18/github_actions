resource "aws_iam_role" "demo" {
  name = "${local.name_prefix}-eks-cluster"

  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
POLICY

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-eks-cluster-role"
  })
}

resource "aws_iam_role_policy_attachment" "demo-AmazonEKSClusterPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.demo.name
}

resource "aws_eks_cluster" "demo" {
  name = var.cluster_name
  # Pinned so two runs months apart produce the same Kubernetes version.
  # Unset, AWS picks its current default and silently drifts.
  version  = var.kubernetes_version
  role_arn = aws_iam_role.demo.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-eks-cluster"
  })

  vpc_config {
    subnet_ids = [
      aws_subnet.private-us-east-1a.id,
      aws_subnet.private-us-east-1b.id,
      aws_subnet.public-us-east-1a.id,
      aws_subnet.public-us-east-1b.id
    ]
  }

  depends_on = [aws_iam_role_policy_attachment.demo-AmazonEKSClusterPolicy]
}
