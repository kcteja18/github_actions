resource "aws_vpc" "main" {
  count      = var.create_vpc ? 1 : 0
  cidr_block = "10.0.0.0/16"

  tags = merge(local.common_tags, {
    Name = local.vpc_name
  })
}

data "aws_vpc" "selected" {
  id = var.create_vpc ? aws_vpc.main[0].id : var.vpc_id
}

locals {
  vpc_id = var.create_vpc ? aws_vpc.main[0].id : data.aws_vpc.selected.id
}
