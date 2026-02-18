provider "aws" { region = var.aws_region }

data "aws_ami" "ubuntu_2204" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

locals {
  cloud_init = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    ssh_user = var.ssh_user
  })
}

resource "aws_instance" "kwok_host" {
  count                       = var.host_count
  ami                         = data.aws_ami.ubuntu_2204.id
  instance_type               = var.instance_type
  key_name                    = var.key_name
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.this.id]
  associate_public_ip_address = true

  user_data                   = local.cloud_init
  user_data_replace_on_change = true

  root_block_device {
    volume_size = var.root_volume_gb
    volume_type = "gp3"
  }

  tags = {
    Name = "${var.name_prefix}-host-${count.index + 1}"
  }

}

resource "null_resource" "wait_hosts" {
  triggers = {
    host_ips = join(",", aws_instance.kwok_host[*].public_ip)
  }

  provisioner "local-exec" {
    command = <<-EOT
      bash -lc 'for ip in $(echo "$TF_HOST_IPS" | tr "," " "); do deadline=$(date +%s); deadline=$(expr "$deadline" + "$TF_WAIT_SECONDS"); while true; do ssh -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "$TF_SSH_KEY" "$TF_SSH_USER@$ip" "cloud-init status --wait >/dev/null 2>&1" >/dev/null 2>&1 && break; now=$(date +%s); if [ "$now" -ge "$deadline" ]; then exit 1; fi; sleep 5; done; done'
    EOT
    environment = {
      TF_HOST_IPS = self.triggers.host_ips
      TF_SSH_USER = var.ssh_user
      TF_SSH_KEY  = var.ssh_private_key_path
      TF_WAIT_SECONDS = var.wait_timeout_seconds
    }
  }
}
