---
title: Kavita
sidebar_position: 53
---

# Kavita

Self-hosted [Kavita](https://www.kavitareader.com/), a folder-scan ebook/manga/comic
reader. Chosen because it needs no Calibre-style library/metadata.db: point it at a
directory tree of EPUB/PDF/CBZ/CBR files and it indexes them directly.

Config: [services/prod/kavita/](https://github.com/IanCou/Hyades/tree/main/services/prod/kavita) · IP/LXC/route: [network.md](../network.md)

## Access posture

LAN/Tailscale only: no public DNS record or Cloudflare Tunnel ingress rule. Same
mechanism as [Cobalt](./cobalt#access-posture).

## Adding books

Drop EPUB/CBZ/etc. files anywhere under `/opt/services/kavita/manga` on the LXC and
trigger a library scan from the UI. No import/conversion step. Bump `disk_size` in
`terraform/envs/prod/main.tf` if the library outgrows local disk.

## References

- [Kavita site](https://www.kavitareader.com/)
- [Kavita Docker install docs](https://wiki.kavitareader.com/installation/docker)
