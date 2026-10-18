# Core service LXCs: all on node1
# Subnet: 10.0.1.0/24 (core tier of the homelab /22)
#
# Migration order matters:
#   1. caddy:      reverse proxy, must come up first
#   2. authentik:  SSO, needed before protecting other services
#   3. everything else:  any order

module "caddy" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 111
  hostname         = "caddy"
  ip_address       = "10.0.1.10/22" # router forwards 80/443 here
  ipv6_address     = "fd00:db8::1:10/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 1024
  disk_size        = 20 # the local xcaddy build needs ~2.4 GB scratch; 10 GB ran out
  tags             = ["core", "docker"]
}

module "authentik" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 112
  hostname         = "authentik"
  ip_address       = "10.0.1.11/22"
  ipv6_address     = "fd00:db8::1:11/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 3072 # authentik is memory-hungry
  disk_size        = 20
  tags             = ["core", "docker"]
}

module "portainer" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 113
  hostname         = "portainer"
  ip_address       = "10.0.1.12/22"
  ipv6_address     = "fd00:db8::1:12/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 10
  tags             = ["core", "docker"]
}

# GitHub Actions self-hosted runner: polls GitHub, runs Ansible deploys
module "github-runner" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 114
  hostname         = "github-runner"
  ip_address       = "10.0.1.13/22"
  ipv6_address     = "fd00:db8::1:13/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048 # needs room for ansible + python deps
  disk_size        = 10
  tags             = ["core", "runner"]
}

module "semaphore" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 115
  hostname         = "semaphore"
  ip_address       = "10.0.1.14/22"
  ipv6_address     = "fd00:db8::1:14/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 1
  memory           = 512
  disk_size        = 10
  tags             = ["core", "docker"]
}

# Tailscale gets its own LXC with special config (TUN device + host networking)
# See docusaurus/docs/stack/tailscale.md for the extra Proxmox config needed
module "tailscale" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 116
  hostname         = "tailscale"
  ip_address       = "10.0.1.15/22"
  ipv6_address     = "fd00:db8::1:15/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 1
  memory           = 512
  disk_size        = 4
  unprivileged     = true # TUN device added manually post-provision via /etc/pve/lxc/116.conf
  tags             = ["core", "docker"]
}

module "adguard" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 117
  hostname         = "adguard"
  ip_address       = "10.0.1.16/22"
  ipv6_address     = "fd00:db8::1:16/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 1
  memory           = 512
  disk_size        = 4
  tags             = ["core", "docker"]
}

# Docusaurus static docs site: builds node image on target, serves via nginx
module "docs" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 118
  hostname         = "docs"
  ip_address       = "10.0.1.17/22"
  ipv6_address     = "fd00:db8::1:17/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048 # node build needs ~1.5GB
  disk_size        = 10
  tags             = ["core", "docker"]
}

module "prometheus" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 119
  hostname         = "prometheus"
  ip_address       = "10.0.1.18/22"
  ipv6_address     = "fd00:db8::1:18/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 1
  memory           = 1024
  disk_size        = 20 # TSDB retention storage
  tags             = ["core", "docker"]
}

module "grafana" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 120
  hostname         = "grafana"
  ip_address       = "10.0.1.19/22"
  ipv6_address     = "fd00:db8::1:19/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 1
  memory           = 1024
  disk_size        = 10
  tags             = ["core", "docker"]
}

module "uptime-kuma" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 121
  hostname         = "uptime-kuma"
  ip_address       = "10.0.1.20/22"
  ipv6_address     = "fd00:db8::1:20/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 1
  memory           = 512
  disk_size        = 10
  tags             = ["core", "docker"]
}

module "ntfy" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 122
  hostname         = "ntfy"
  ip_address       = "10.0.1.21/22"
  ipv6_address     = "fd00:db8::1:21/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 1
  memory           = 512
  disk_size        = 10
  tags             = ["core", "docker"]
}

# Barebones SSH jump host: LAN-only, no service stack.
module "jump" {
  source = "../../modules/lxc-docker"

  node_name          = "node1"
  vm_id              = 123
  hostname           = "jump"
  ip_address         = "10.0.1.22/22"
  ipv6_address       = "fd00:db8::1:22/64"
  gateway            = var.gateway
  template_file_id   = var.template_file_id
  ssh_public_key     = var.ssh_public_key
  dns_search_domains = ["example.internal", "example.com"]
  dns_servers        = ["10.0.1.16"] # AdGuard: the only resolver that knows example.internal
  cores              = 1
  memory             = 256
  disk_size          = 4
  tags               = ["core"]
}

module "speedtest" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 124
  hostname         = "speedtest"
  ip_address       = "10.0.1.23/22"
  ipv6_address     = "fd00:db8::1:23/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 1
  memory           = 512
  disk_size        = 4
  tags             = ["core", "docker"]
}
