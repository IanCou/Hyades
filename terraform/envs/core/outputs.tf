output "container_ips" {
  description = "IPs for Ansible inventory: update ansible/inventory/hosts.yml with these"
  value = {
    caddy         = module.caddy.ip_address
    adguard       = module.adguard.ip_address
    authentik     = module.authentik.ip_address
    portainer     = module.portainer.ip_address
    tailscale     = module.tailscale.ip_address
    github-runner = module.github-runner.ip_address
    docs          = module.docs.ip_address
  }
}
