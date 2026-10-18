output "container_ips" {
  description = "IP addresses of all prod containers (use these in Ansible inventory)"
  value = {
    immich    = module.immich.ip_address
    nextcloud = module.nextcloud.ip_address
    coolify   = module.coolify.ip_address
  }
}
