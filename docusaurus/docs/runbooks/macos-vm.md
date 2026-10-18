# macOS VM on Proxmox (OpenCore)

End-to-end recipe for running macOS as a Proxmox VM using
[LongQT-sea/OpenCore-ISO](https://github.com/LongQT-sea/OpenCore-ISO) as the
bootloader. Source of truth for VM 401 (`macosvm00`, node2). Read the
upstream README too; that's where the CPU/network compatibility tables
come from; this runbook is the cluster-specific layer.

## Prerequisites

- A Proxmox node with **at least 30 GB physical free** on `local-lvm`
  (thin pools overcommit virtually but a real install writes ~15–20 GB).
- The host CPU: Intel preferred. AMD works but needs extra `-cpu` flag
  removals (see upstream README footnote 1).
- Decide macOS version up front; it sets the CPU model + network adapter.

## 1 · Stage the OpenCore ISO

```bash
ssh root@<node>
cd /var/lib/vz/template/iso/
wget https://github.com/LongQT-sea/OpenCore-ISO/releases/download/v0.7/LongQT-OpenCore-v0.7.iso
```

(~16 MB, OpenCore only; no macOS bundled.)

## 2 · Create the VM

For macOS 13 – 26 on Intel:

```bash
qm create <vmid> \
  --name macOS \
  --machine q35 \
  --bios ovmf \
  --efidisk0 local-lvm:0,efitype=4m,pre-enrolled-keys=0 \
  --cores 2 --sockets 1 \
  --memory 4096 --balloon 0 \
  --net0 virtio,bridge=vmbr0 \
  --scsihw virtio-scsi-single \
  --sata0 local-lvm:64,ssd=1,discard=on \
  --ide2 local:iso/LongQT-OpenCore-v0.7.iso,media=cdrom \
  --boot 'order=ide2;sata0' \
  --agent enabled=1 \
  --ostype other

# macOS 13+ needs the CPU set via -args (not --cpu) so Proxmox doesn't
# inject +kvm_pv_eoi,+kvm_pv_unhalt which break boot on AMD and aren't
# needed on Intel either:
qm set <vmid> --args '-cpu Skylake-Client-v4,vendor=GenuineIntel'
```

Cores must be a power of two (1/2/4/8/…); use multiple sockets for odd
counts (see upstream README).

For other macOS versions, swap the CPU model and net adapter per upstream
table. For AMD hosts: `qm set <vmid> -delete <flag>` not enough; see
upstream footnote on `pcid` / `spec-ctrl`.

## 3 · Fetch the recovery image

The upstream `macos-iso-builder` releases were taken down for legal
reasons. Pull directly from Apple via Acidanthera's
[`macrecovery.py`](https://github.com/acidanthera/OpenCorePkg/tree/master/Utilities/macrecovery):

```bash
apt-get install -y xorriso dmg2img python3
mkdir -p /root/macrecovery && cd /root/macrecovery
curl -sSL -O https://raw.githubusercontent.com/acidanthera/OpenCorePkg/master/Utilities/macrecovery/macrecovery.py
curl -sSL -O https://raw.githubusercontent.com/acidanthera/OpenCorePkg/master/Utilities/macrecovery/boards.json

# Pick a board ID mapped to your desired macOS version in boards.json.
# "latest" entries → current macOS (Tahoe at time of writing).
python3 macrecovery.py -b Mac-A61BADE1FDAD7B05 -m 00000000000000000 -os latest download
# → com.apple.recovery.boot/BaseSystem.dmg + BaseSystem.chunklist
```

`-os latest` returns the build the _board_ was last shipped with. To
target a specific version, find a board ID whose value in `boards.json`
matches (e.g. `Mac-B4831CEBD52A0C4C` → 13.7.8 for Ventura).

## 4 · Attach the recovery as a raw disk (not ISO)

> **Don't bother with an ISO9660 wrapper.** OpenCore's scanner does not
> reliably pick up `com.apple.recovery.boot/` from CD-ROM media. Convert
> to raw and attach as a disk; OpenCore reads the APFS container
> directly and surfaces a "macOS Base System" boot entry.

```bash
dmg2img com.apple.recovery.boot/BaseSystem.dmg /root/macrecovery/BaseSystem.img
# 914 MB DMG → 2.5 GB raw (writes all sectors, not thin-friendly)

qm importdisk <vmid> /root/macrecovery/BaseSystem.img local-lvm --format raw
qm set <vmid> --sata1 local-lvm:vm-<vmid>-disk-2
qm set <vmid> --boot 'order=ide2;sata0;sata1'
qm start <vmid>
```

## 5 · Install macOS via the console

Open the Proxmox web UI → VM → Console. Keyboard-only: noVNC mouse
capture is unreliable in OpenCore's GUI picker.

OpenCore picker keys: **← →** navigate, **Enter** select, **Esc** back,
**Spacebar** toggle aux entries (Reset NVRAM / Toggle SIP).

1. OpenCore picker → **macOS Base System** → Enter.
2. Recovery menu → **Disk Utility** → Continue.
3. View → **Show All Devices**. Pick the **64 GB SATA** disk (not the
   2.5 GB recovery disk!). Erase as APFS / GUID Partition Map, name
   `Macintosh HD`.
4. Quit Disk Utility → **Reinstall macOS Tahoe** → pick `Macintosh HD`.
5. Installer downloads ~14 GB and reboots several times. **Each reboot,
   pick "macOS Installer" (or "macOS Install Data") at the OpenCore
   picker** until the final boot into Setup Assistant.
6. Skip iCloud at setup; configure later after VMHide.kext is in place.

## 6 · Post-install: make it bootable without the OpenCore CD

Inside macOS, on the desktop there's a `LongQT-OpenCore` volume:

1. Run `Mount_EFI.command` → mounts the EFI partition of the target
   disk.
2. Copy `LongQT-OpenCore/EFI_RELEASE/EFI` to the mounted EFI partition.
3. Run `Install_Python3.command` (lots of helper tools need it).
4. Copy `Mount_EFI.command`, `ProperTree`, `GenSMBIOS` to the Desktop
   for future `config.plist` edits.
5. Detach the OpenCore CD: `qm set <vmid> --delete ide2`.
6. Delete the recovery raw disk to reclaim space:
   `qm set <vmid> --delete sata1` then `qm disk unlink <vmid> --idlist sata1`
   (or use the UI: Hardware → select disk → Detach → Remove).

## 7 · Optional fixes

### iCloud / iMessage / iServices

Generate your own SMBIOS via [GenSMBIOS](https://github.com/corpnewt/GenSMBIOS)
and edit `EFI/OC/config.plist` with [ProperTree](https://github.com/corpnewt/ProperTree).
Follow [Dortania's iServices guide](https://dortania.github.io/OpenCore-Post-Install/universal/iservices.html).

macOS 15 / 26 additionally need [VMHide.kext](https://github.com/zhen-zen/VMHide).

### Tahoe cursor freeze

macOS 26 has a cursor freeze bug on QEMU's standard pointer. Workarounds
(any one):

- Toggle "Use tablet for pointer" off in VM Options.
- Use `virtio-tablet` instead. Append to existing `-cpu` args:

  ```bash
  # Read current args first; qm set --args replaces the whole string
  qm config <vmid> | grep ^args:
  # → args: -cpu Skylake-Client-v4,vendor=GenuineIntel
  qm set <vmid> --args '-cpu Skylake-Client-v4,vendor=GenuineIntel -device virtio-tablet'
  ```

  Middle-click on a real mouse becomes right-click in the VM with
  virtio-tablet.

- Most reliable: passthrough a physical mouse + keyboard + iGPU/dGPU,
  or use VNC/Chrome Remote Desktop instead of noVNC.

### Disable SIP

OpenCore picker → Spacebar → **Toggle SIP** → Enter. Reboots; SIP
disabled state persists in NVRAM.

## Cluster-specific notes

- All three nodes are i5-8500 (Coffee Lake, AVX2), confirmed via
  `/proc/cpuinfo` on each. Skylake-Client-v4 works on all three (VM 401 lives
  on node2).
- All three nodes use `vmbr0` as the main bridge.
- Don't drop a macOS VM on a node with `<30 GB` physical free on
  `local-lvm`. Migrate other VMs off first (see [Node failure](./node-failure)).
