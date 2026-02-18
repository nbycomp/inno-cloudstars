output "host_public_ips" {
  value = aws_instance.kwok_host[*].public_ip
  description = "Public IPs of KWOK hosts"
}
