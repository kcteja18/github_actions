resource "aws_internet_gateway" "igw" {
  count  = var.create_vpc ? 1 : 0
  vpc_id = local.vpc_id

  tags = merge(local.common_tags, {
    Name = local.igw_name
  })
}
