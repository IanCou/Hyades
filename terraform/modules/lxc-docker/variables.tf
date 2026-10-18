variable "node_name" {
  description = "Proxmox node to create the container on"
  type        = string
}

variable "vm_id" {
  description = "Proxmox container ID (must be unique)"
  type        = number
}

variable "hostname" {
  description = "Container hostname"
  type        = string
}

variable "ip_address" {
  description = "Static IP in CIDR notation, e.g. 10.0.0.50/22"
  type        = string
}

variable "ipv6_address" {
  description = <<-EOT
    Optional static IPv6 in CIDR notation, e.g. fd00:db8::1:10/64.
    Additive alongside the SLAAC addresses the container already gets from
    router advertisements on this LAN (fd00:db8::/64 ULA + a
    2600:.../64 ISP-delegated public prefix); this just gives it a second,
    stable address in the same already-live ULA prefix for internal DNS to
    point at, deterministically derived from ip_address's last two octets.
  EOT
  type        = string
  default     = null
}

variable "gateway" {
  description = "Default gateway"
  type        = string
}

variable "template_file_id" {
  description = "Proxmox CT template, e.g. local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"
  type        = string
}

variable "ssh_public_key" {
  description = "SSH public key to inject (for root login)"
  type        = string
}

variable "cores" {
  description = "vCPU count"
  type        = number
  default     = 2
}

variable "memory" {
  description = "RAM in MB"
  type        = number
  default     = 2048
}

variable "disk_size" {
  description = "Root disk size in GB"
  type        = number
  default     = 20
}

variable "datastore_id" {
  description = "Proxmox storage pool for the disk"
  type        = string
  default     = "local-lvm"
}

variable "bridge" {
  description = "Network bridge"
  type        = string
  default     = "vmbr0"
}

variable "tags" {
  description = "Proxmox tags"
  type        = list(string)
  default     = []
}

variable "unprivileged" {
  description = "Run as unprivileged container (recommended)"
  type        = bool
  default     = true
}

variable "dns_search_domains" {
  description = <<-EOT
    Optional list of DNS search domains (resolv.conf `search` line), e.g.
    ["example.internal", "example.com"]. Proxmox's searchdomain
    field takes one space-separated string, so the list is joined below.
  EOT
  type        = list(string)
  default     = []
}

variable "dns_servers" {
  description = <<-EOT
    Optional list of nameservers (resolv.conf `nameserver` lines). Only
    needed when a container must resolve names that aren't in public DNS,
    e.g. the *.example.internal / *.example.com AdGuard rewrites
    (10.0.1.16), which the default Proxmox-supplied ISP resolver has
    never heard of. Leave unset to inherit the node's default resolver.
  EOT
  type        = list(string)
  default     = []
}

variable "mount_points" {
  description = "List of bind mount points: {volume = host_path, path = container_path}"
  type = list(object({
    volume = string
    path   = string
  }))
  default = []
}
