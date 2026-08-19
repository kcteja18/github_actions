resource "aws_route_table" "private" {
  vpc_id = local.vpc_id

  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.nat[0].id
    }
  }

  tags = merge(local.common_tags, {
    Name = local.private_route_table_name
  })
}

resource "aws_route_table" "public" {
  vpc_id = local.vpc_id

  dynamic "route" {
    for_each = var.create_vpc || length(trimspace(var.internet_gateway_id)) > 0 ? [1] : []
    content {
      cidr_block = "0.0.0.0/0"
      gateway_id = var.create_vpc ? aws_internet_gateway.igw[0].id : var.internet_gateway_id
    }
  }

  tags = merge(local.common_tags, {
    Name = local.public_route_table_name
  })
}

resource "aws_route_table_association" "private-us-east-1a" {
  subnet_id      = aws_subnet.private-us-east-1a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private-us-east-1b" {
  subnet_id      = aws_subnet.private-us-east-1b.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "public-us-east-1a" {
  subnet_id      = aws_subnet.public-us-east-1a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public-us-east-1b" {
  subnet_id      = aws_subnet.public-us-east-1b.id
  route_table_id = aws_route_table.public.id
}
