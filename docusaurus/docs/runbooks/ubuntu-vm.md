# Ubuntu Desktop VM on Proxmox

Recipe for a personal Ubuntu 24.04 LTS Desktop (GNOME) VM. Source of
truth for VM 403 (`ubuntuvm00`, node3).

If you're driving the install/config over the Proxmox console instead of
SPICE/noVNC (no client installed, no network access to the guest yet),
see [Driving a QEMU VM console headlessly](./qemu-console-automation) for
the `screendump`/`sendkey` technique and its gotchas; this doc assumes
you're either doing that or clicking through normally.

## Prerequisites

- ~7 GB free on `local-lvm` for the ISO, 60 GB for the disk.
- Ubuntu Desktop 24.04 ISO: `https://releases.ubuntu.com/24.04/` (check
  the actual current point release filename; it drifts, e.g. `24.04.4`).
- **`libgl1` and `libegl1` installed on the target node**. See the
  display gotcha below. Without them, `vga: virtio-gl` fails outright.

## The `qxl` → `virtio` → `virtio-gl` display saga

Don't use `vga: qxl` for this VM; it's a known incompatibility with
modern Ubuntu/GNOME and produces a **persistent black screen** (X
starts, cursor shows, GNOME Shell never paints).

What actually works, discovered the hard way:

1. **`vga: virtio` (no GL) + bumped VRAM** (`memory=64`) gets GNOME
   Shell's own compositor rendering: the live-session desktop shows up
   fine.
2. **The installer app itself still needed GL**: it rendered as a
   blank white window under plain `virtio`, because Ubuntu's installer
   (Flutter-based since 23.10+) requires GL acceleration that plain
   `virtio` doesn't provide.
3. **`vga: virtio-gl,memory=64`** fixes the installer, but requires
   `libgl1`/`libegl1` on the **Proxmox host** (`apt install libgl1
libegl1` on the node, a real missing host dependency, not a VM
   misconfiguration). Without them, `qm start` fails outright with
   `missing libraries for 'virtio-gl' detected!`.
4. **Caveat:** `virtio-gl`'s screendump via `qm monitor` returns
   `Error: no surface`, fine for actual use over noVNC/SPICE, but if
   you're scripting console verification via `screendump`, switch back
   to plain `virtio` after the install finishes (GNOME Shell itself
   doesn't need the GL path once installed, just the installer did).

```bash
qm set 403 --vga virtio,memory=64      # day-to-day desktop use
qm set 403 --vga virtio-gl,memory=64   # only while running the installer
```

## 1 · Create the VM

```bash
qm create 403 \
  --name ubuntuvm00 \
  --machine q35 \
  --bios ovmf \
  --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=0 \
  --cpu host \
  --cores 4 \
  --memory 8192 \
  --balloon 0 \
  --vga virtio-gl,memory=64 \
  --scsihw virtio-scsi-pci \
  --scsi0 local-lvm:60 \
  --ide2 local:iso/ubuntu-24.04.4-desktop-amd64.iso,media=cdrom \
  --boot order=ide2\;scsi0 \
  --net0 virtio,bridge=vmbr0 \
  --agent enabled=1

qm start 403
```

## 2 · Install via the graphical installer

Boot to GRUB → "Try or Install Ubuntu" (auto-boots after ~12s) → the
Ubuntu Desktop installer wizard. Answers used:

| Screen               | Answer                                                                                                            |
| -------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Language             | English                                                                                                           |
| Accessibility        | skip (defaults)                                                                                                   |
| Keyboard layout      | English (US), auto-detected                                                                                       |
| Internet connection  | Use wired connection                                                                                              |
| Updates              | **Skip** (don't update the installer mid-flow)                                                                    |
| Type of installation | Install Ubuntu                                                                                                    |
| Installation mode    | Interactive installation                                                                                          |
| Applications         | Default selection (minimal)                                                                                       |
| Optimise             | Leave both checkboxes unchecked                                                                                   |
| Disk setup           | **Erase disk and install Ubuntu** (fine, fresh VM disk)                                                           |
| Account              | Name `Ian`, computer name `ubuntuvm00`, username `ian`, password set, **"Require my password to log in" checked** |
| Timezone             | Auto-detected `America/New_York`; confirm it's right                                                              |

Install takes ~10-15 minutes (copying files, then a slower "Setting up
the system..." package-configuration phase). On completion, **detach
the ISO before clicking Restart**; otherwise the guest's own reboot
request can get stuck waiting on the management layer:

```bash
qm set 403 --ide2 none,media=cdrom
qm set 403 --boot order=scsi0
```

Then click "Restart now". If it hangs mid-shutdown (CPU still busy,
screen frozen) longer than a minute or two, `qm reset 403` forces it
through, safe once the ISO is detached and the install is confirmed
complete.

After first boot, switch off `virtio-gl` for normal use:

```bash
qm stop 403
qm set 403 --vga virtio,memory=64
qm start 403
```

## 3 · Post-install configuration

Log in, open a terminal (Super key → type `terminal` → Enter), then:

```bash
# Check the actual connection name first; netplan-managed connections
# are named "netplan-<device>", not "Wired connection 1"
nmcli con show

sudo nmcli con mod "netplan-enp6s18" \
  ipv4.method manual \
  ipv4.addresses 10.0.0.47/22 \
  ipv4.gateway 10.0.0.1 \
  ipv4.dns "10.0.1.16 10.0.0.3"
sudo nmcli con up "netplan-enp6s18"

# SSH + guest agent + spice: none of these ship on Ubuntu Desktop by default
sudo apt update && sudo apt install -y openssh-server spice-vdagent qemu-guest-agent

# SSH key (get the key from terraform/envs/*/terraform.tfvars, ssh_public_key)
mkdir -p $HOME/.ssh && chmod 700 $HOME/.ssh
echo "ssh-ed25519 AAAA... you@host" >> $HOME/.ssh/authorized_keys
chmod 600 $HOME/.ssh/authorized_keys

sudo systemctl start qemu-guest-agent spice-vdagentd
```

`qemu-guest-agent` and `spice-vdagentd` are Debian/Ubuntu **static
units**: no `systemctl enable` needed, `start` is enough.

**Gotcha:** Ubuntu's automatic "Software Updater" GUI can pop up
mid-session and steal keyboard focus with a polkit auth dialog;
if a typed command seems to vanish, check for that dialog and
dismiss/cancel it before retyping.

## Verify

```bash
ping -c1 10.0.0.47
ssh ian@10.0.0.47 whoami
ssh root@node3 "qm agent 403 ping"   # empty output = success
```
