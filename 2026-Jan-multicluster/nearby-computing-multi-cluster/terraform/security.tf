resource "aws_security_group" "this" {
  name        = "${var.name_prefix}-sg"
  description = "KWOK host security group"
  vpc_id      = aws_vpc.this.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

locals {
  sg_allowed_cidrs = concat([var.my_ip_cidr], var.extra_ip_cidrs)
  api_port_range   = { from = 30000, to = 39999 }
  common_tags      = { Name = "${var.name_prefix}-sg" }
}

resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.this.id
  description       = "SSH from my IP"
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
  cidr_ipv4         = var.my_ip_cidr

  tags = {
    Name = "multi cluster ssh ${replace(var.my_ip_cidr, ".", "-")}"
  }
}

resource "aws_vpc_security_group_ingress_rule" "api_ports" {
  for_each          = toset(local.sg_allowed_cidrs)
  security_group_id = aws_security_group.this.id
  description       = "Cluster API and metrics ports (dev)"
  from_port         = local.api_port_range.from
  to_port           = local.api_port_range.to
  ip_protocol       = "tcp"
  cidr_ipv4         = each.value

  tags = {
    Name = "cluster api and metrics ${each.value}"
  }
}
