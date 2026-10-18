# Test LXCs: one per Docker Compose stack
# Subnet: 10.0.3.0/24 (test tier of the homelab /22)

module "n8n" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 601
  hostname         = "n8n"
  ip_address       = "10.0.3.10/22"
  ipv6_address     = "fd00:db8::3:10/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 20
  tags             = ["test", "docker"]
}

module "kafka" {
  source = "../../modules/lxc-docker"

  node_name        = "node2"
  vm_id            = 603
  hostname         = "kafka"
  ip_address       = "10.0.3.12/22"
  ipv6_address     = "fd00:db8::3:12/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 4096
  disk_size        = 30
  tags             = ["test", "docker"]
}

module "internship_watcher" {
  source = "../../modules/lxc-docker"

  node_name        = "node2"
  vm_id            = 602
  hostname         = "internship-watcher"
  ip_address       = "10.0.3.11/22"
  ipv6_address     = "fd00:db8::3:11/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 1
  memory           = 1024
  disk_size        = 8
  tags             = ["test", "docker"]
}

module "openclaw" {
  source = "../../modules/lxc-docker"

  node_name        = "node2"
  vm_id            = 604
  hostname         = "openclaw"
  ip_address       = "10.0.3.13/22"
  ipv6_address     = "fd00:db8::3:13/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 20
  tags             = ["test", "docker"]
}

# Personal dev box: Docker + Claude Code CLI, no fixed compose stack.
module "dev" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 605
  hostname         = "dev"
  ip_address       = "10.0.3.14/22"
  ipv6_address     = "fd00:db8::3:14/64"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 4
  memory           = 8192
  disk_size        = 80
  tags             = ["test", "docker", "dev"]
}
