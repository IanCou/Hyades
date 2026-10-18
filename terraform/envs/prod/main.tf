# Prod LXCs: one per Docker Compose stack
# Subnet: 10.0.2.0/24 (prod tier of the homelab /22)

module "immich" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 211
  hostname         = "immich"
  ip_address       = "10.0.2.10/22"
  ipv6_address     = "fd00:db8::2:10/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 4
  memory           = 4096
  disk_size        = 40
  tags             = ["prod", "docker"]
  mount_points     = [{ volume = "/mnt/nas/immich", path = "/mnt/nas/immich" }]
}

module "nextcloud" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 212
  hostname         = "nextcloud"
  ip_address       = "10.0.2.11/22"
  ipv6_address     = "fd00:db8::2:11/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 20
  tags             = ["prod", "docker"]
  mount_points     = [{ volume = "/mnt/nas/nextcloud", path = "/mnt/nas/nextcloud" }]
}

module "coolify" {
  source = "../../modules/lxc-docker"

  node_name        = "node3"
  vm_id            = 213
  hostname         = "coolify"
  ip_address       = "10.0.2.12/22"
  ipv6_address     = "fd00:db8::2:12/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 4096
  disk_size        = 40
  tags             = ["prod", "docker"]
}

module "searxng" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 214
  hostname         = "searxng"
  ip_address       = "10.0.2.13/22"
  ipv6_address     = "fd00:db8::2:13/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 1
  memory           = 512
  disk_size        = 4
  tags             = ["prod", "docker"]
}

module "airtrail" {
  source = "../../modules/lxc-docker"

  node_name        = "node3"
  vm_id            = 217
  hostname         = "airtrail"
  ip_address       = "10.0.2.16/22"
  ipv6_address     = "fd00:db8::2:16/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 20
  tags             = ["prod", "docker"]
}

# Self-hosted cobalt.tools media-downloader API. No Caddy route / public DNS;
# Tailscale + LAN only via cobalt.example.internal, same posture as airtrail.
module "cobalt" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 218
  hostname         = "cobalt"
  ip_address       = "10.0.2.17/22"
  ipv6_address     = "fd00:db8::2:17/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 16
  tags             = ["prod", "docker"]
}

module "kavita" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 219
  hostname         = "kavita"
  ip_address       = "10.0.2.18/22"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 20
  tags             = ["prod", "docker"]
}

module "audiobookshelf" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 220
  hostname         = "audiobookshelf"
  ip_address       = "10.0.2.19/22"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 20
  tags             = ["prod", "docker"]
}

module "appdev00" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 221
  hostname         = "appdev00"
  ip_address       = "10.0.2.20/22"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 8192
  disk_size        = 40
  tags             = ["prod", "docker"]
}

module "homeassistant" {
  source = "../../modules/lxc-docker"

  node_name        = "node3"
  vm_id            = 223
  hostname         = "homeassistant"
  ip_address       = "10.0.2.22/22"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 20
  tags             = ["prod", "docker"]
}
