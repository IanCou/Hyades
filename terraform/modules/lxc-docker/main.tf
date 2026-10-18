terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.102"
    }
  }
}

resource "proxmox_virtual_environment_container" "this" {
  node_name    = var.node_name
  vm_id        = var.vm_id
  tags         = var.tags
  unprivileged = var.unprivileged

  # Docker requires these in unprivileged containers
  features {
    nesting = true
  }

  initialization {
    hostname = var.hostname

    ip_config {
      ipv4 {
        address = var.ip_address
        gateway = var.gateway
      }

      dynamic "ipv6" {
        for_each = var.ipv6_address == null ? [] : [var.ipv6_address]
        content {
          address = ipv6.value
        }
      }
    }

    user_account {
      keys = [var.ssh_public_key]
    }

    dynamic "dns" {
      for_each = length(var.dns_search_domains) == 0 && length(var.dns_servers) == 0 ? [] : [1]
      content {
        domain  = length(var.dns_search_domains) == 0 ? null : join(" ", var.dns_search_domains)
        servers = length(var.dns_servers) == 0 ? null : var.dns_servers
      }
    }
  }

  operating_system {
    template_file_id = var.template_file_id
    type             = "debian"
  }

  cpu {
    cores = var.cores
  }

  memory {
    dedicated = var.memory
  }

  disk {
    datastore_id = var.datastore_id
    size         = var.disk_size
  }

  network_interface {
    name   = "eth0"
    bridge = var.bridge
  }

  dynamic "mount_point" {
    for_each = var.mount_points
    content {
      volume = mount_point.value.volume
      path   = mount_point.value.path
    }
  }

  start_on_boot = true
  started       = true

  lifecycle {
    ignore_changes = [
      initialization[0].user_account,
      operating_system[0].template_file_id,
    ]
  }
}
