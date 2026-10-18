---
title: Immich
sidebar_position: 35
---

# Immich

Self-hosted photo backup. Library lives on the NAS (`10.0.0.249:/volume1/Ian/immich`
→ `/mnt/nas/immich`). Publicly reachable through the Cloudflare tunnel.

Config: [services/prod/immich/](https://github.com/IanCou/Hyades/tree/main/services/prod/immich) · IP/LXC/route: [network.md](../network.md)

## NAS permissions

Data dirs under `/mnt/nas/immich` are **mode 777**. This sidesteps the
[unprivileged LXC uid mapping](../unprivileged-lxc.md) issue entirely: any uid inside
the container can read/write. Fine for Immich because the LXC isn't shared and data is
already behind Tailscale.

## NFS path wiring

The NFS mount is made on the Proxmox host and bind-mounted into the LXC via `mp0:` in
`/etc/pve/lxc/211.conf`. Unprivileged LXCs cannot mount NFS directly.

## References

- [Immich docs](https://immich.app/docs)
- [Immich docker-compose](https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml)
