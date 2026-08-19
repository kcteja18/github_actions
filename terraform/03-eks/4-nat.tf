resource "aws_eip" "nat" {
  count = var.enable_nat_gateway ? 1 : 0
  # `domain` replaces the `vpc` argument, which was removed in AWS provider v5.
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = local.nat_eip_name
  })
}

resource "aws_nat_gateway" "nat" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public-us-east-1a.id

  tags = merge(local.common_tags, {
    Name = local.nat_gateway_name
  })

  depends_on = [aws_internet_gateway.igw]
}
