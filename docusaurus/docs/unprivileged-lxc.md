---
title: Unprivileged LXC uid mapping
sidebar_position: 20
---

# Unprivileged LXC uid mapping

All LXCs here run **unprivileged** (`unprivileged: 1` in `/etc/pve/lxc/NNN.conf`).
Proxmox remaps container UIDs into a high range on the host:

```
container uid 0      → host uid 100000 (LXC "root")
container uid N      → host uid 100000 + N
container uid 65534  → host uid 165534
```

Default range spans 65536 IDs starting at 100000.

## Why it matters

Any storage shared between the host and LXC (NFS bind mounts, zfs
datasets, etc.) has ownership recorded with **host** UIDs. A file owned
by `33:33` on the host shows up as `nobody:nobody` inside the LXC (because
host uid 33 is not in the LXC's mapped range).

## Fix patterns

Three options, in order of preference:

1. **Chown on host to the mapped uid**: easiest.
   For container uid 33 (www-data): `chown -R 100033:100033 /path` on the
   Proxmox node.

2. **Open permissions**: `chmod 777`. Fine for low-risk data dirs (Immich
   uses this). Avoid for anything private.

3. **`lxc.idmap` in container conf**: map a single uid directly (e.g.
   container 33 → host 33). Most flexible, most complex; needs matching
   `/etc/subuid` + `/etc/subgid` entries on the Proxmox node.

## Services affected here

- [Nextcloud](./stack/nextcloud.md): fix #1, data dir owned by 100033:100033
- [Immich](./stack/immich.md): fix #2, dirs are 777

## References

- [Proxmox unprivileged containers](https://pve.proxmox.com/wiki/Unprivileged_LXC_containers)
- [LXC `lxc.idmap`](https://linuxcontainers.org/lxc/manpages/man5/lxc.container.conf.5.html)
