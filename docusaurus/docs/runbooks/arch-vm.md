# Arch Linux Desktop VM on Proxmox

Recipe for a personal Arch Linux + XFCE desktop VM, installed via
`archinstall`. Source of truth for VM 402 (`archvm00`, node2).

If you're driving the install/config over the Proxmox console instead of
SPICE/noVNC (no client installed, no network access to the guest yet),
see [Driving a QEMU VM console headlessly](./qemu-console-automation) for
the `screendump`/`sendkey` technique and its gotchas; this doc assumes
you're either doing that or clicking through normally.

## Prerequisites

- ~2 GB free on `local-lvm` for the ISO, 60 GB for the disk.
- Latest Arch ISO: `https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso`

## 1 · Create the VM

```bash
qm create 402 \
  --name archvm00 \
  --machine q35 \
  --bios ovmf \
  --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=0 \
  --cpu host \
  --cores 4 \
  --memory 8192 \
  --balloon 0 \
  --vga qxl \
  --scsihw virtio-scsi-pci \
  --scsi0 local-lvm:60 \
  --ide2 local:iso/archlinux-x86_64.iso,media=cdrom \
  --boot order=scsi0\;ide2 \
  --net0 virtio,bridge=vmbr0 \
  --agent enabled=1

qm start 402
```

`vga: qxl` renders fine for XFCE (unlike Ubuntu/GNOME; see the
[Ubuntu VM runbook](./ubuntu-vm) for why that one needed `virtio` instead).

## 2 · Install via `archinstall`

Boot to the live shell, confirm network (DHCP works automatically), then:

```bash
archinstall
```

Answers used for `archvm00`:

| Screen                | Answer                                                                        |
| --------------------- | ----------------------------------------------------------------------------- |
| Locale/Mirror region  | US mirrors                                                                    |
| Disk configuration    | Best-effort default partition layout, `ext4`                                  |
| Disk encryption       | None                                                                          |
| Bootloader            | `systemd-boot` (default)                                                      |
| Hostname              | `archvm00`                                                                    |
| Root password         | set                                                                           |
| User account          | `ian`, `wheel` group (sudo)                                                   |
| Profile               | Desktop → **Xfce4**, `lightdm` greeter                                        |
| Audio                 | `pipewire`                                                                    |
| Network configuration | **Use NetworkManager** (not manual; easier to set the static IP post-install) |
| Additional packages   | `openssh`                                                                     |
| Optional repositories | none (multilib skipped)                                                       |
| Timezone              | `America/New_York` (⚠ don't pick bare `EST`: no DST)                          |

Confirm and let it install (~2 minutes), then `reboot` when it offers to.
The ISO auto-detaches; if it doesn't, `qm set 402 --ide2 none,media=cdrom`
before rebooting to avoid landing back in the installer.

## 3 · Post-install configuration

Log in at the lightdm greeter, open a terminal (Alt+F2 → `xfce4-terminal`
if there's no launcher handy), then:

```bash
# Static IP
sudo nmcli con mod "Wired connection 1" \
  ipv4.method manual \
  ipv4.addresses 10.0.0.46/22 \
  ipv4.gateway 10.0.0.1 \
  ipv4.dns "10.0.1.16 10.0.0.3"
sudo nmcli con up "Wired connection 1"

# SSH key (get the key from terraform/envs/*/terraform.tfvars, ssh_public_key)
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "ssh-ed25519 AAAA... you@host" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
sudo systemctl start sshd  # already enabled if openssh was in Additional packages

# Console/guest agent polish
sudo pacman -S --noconfirm spice-vdagent qemu-guest-agent
sudo systemctl start spice-vdagentd qemu-guest-agent
```

`qemu-guest-agent` and `spice-vdagentd` are Arch **static units**: no
`systemctl enable` needed, `start` is enough and they'll come up on
every boot automatically.

## Verify

```bash
ping -c1 10.0.0.46
ssh ian@10.0.0.46 whoami
ssh root@node2 "qm agent 402 ping"   # empty output = success
```
