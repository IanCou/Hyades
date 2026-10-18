variable "proxmox_endpoint" {
  description = "Proxmox API URL, e.g. https://10.0.0.10:8006/"
  type        = string
}

variable "proxmox_api_token" {
  description = "API token: user@realm!tokenid=secret"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key injected into every container"
  type        = string
}

variable "gateway" {
  description = "LAN gateway"
  type        = string
  default     = "10.0.0.1"
}

variable "template_file_id" {
  description = "CT template on Proxmox storage"
  type        = string
  default     = "local:vztmpl/debian-12-standard_12.12-1_amd64.tar.zst"
}
