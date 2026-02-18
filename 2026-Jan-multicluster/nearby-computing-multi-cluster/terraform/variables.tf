variable "aws_region" { type = string }
variable "availability_zone" { type = string }
variable "name_prefix" { type = string }

variable "my_ip_cidr" { type = string }
variable "extra_ip_cidrs" {
  type    = list(string)
  default = []
}
variable "ssh_user" { type = string }
variable "key_name" { type = string }
variable "ssh_private_key_path" { type = string }

variable "host_count" { type = number }
variable "instance_type" { type = string }
variable "root_volume_gb" { type = number }

variable "vpc_cidr" { type = string }
variable "public_subnet_cidr" { type = string }

variable "wait_timeout_seconds" {
  type    = number
  default = 90
}
