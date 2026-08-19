data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  availability_zones = slice(data.aws_availability_zones.available.names, 0, min(2, length(data.aws_availability_zones.available.names)))
}

resource "aws_subnet" "private-us-east-1a" {
  vpc_id            = local.vpc_id
  cidr_block        = var.private_subnet_cidrs[0]
  availability_zone = local.availability_zones[0]

  tags = merge(local.common_tags, {
    Name                                        = "${local.name_prefix}-private-${local.availability_zones[0]}"
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
  })
}

resource "aws_subnet" "private-us-east-1b" {
  vpc_id            = local.vpc_id
  cidr_block        = var.private_subnet_cidrs[1]
  availability_zone = length(local.availability_zones) > 1 ? local.availability_zones[1] : local.availability_zones[0]

  tags = merge(local.common_tags, {
    Name                                        = "${local.name_prefix}-private-${length(local.availability_zones) > 1 ? local.availability_zones[1] : local.availability_zones[0]}"
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
  })
}

resource "aws_subnet" "public-us-east-1a" {
  vpc_id                  = local.vpc_id
  cidr_block              = var.public_subnet_cidrs[0]
  availability_zone       = local.availability_zones[0]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name                                        = "${local.name_prefix}-public-${local.availability_zones[0]}"
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
  })
}

resource "aws_subnet" "public-us-east-1b" {
  vpc_id                  = local.vpc_id
  cidr_block              = var.public_subnet_cidrs[1]
  availability_zone       = length(local.availability_zones) > 1 ? local.availability_zones[1] : local.availability_zones[0]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name                                        = "${local.name_prefix}-public-${length(local.availability_zones) > 1 ? local.availability_zones[1] : local.availability_zones[0]}"
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
  })
}
