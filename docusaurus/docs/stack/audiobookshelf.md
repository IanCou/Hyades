---
title: Audiobookshelf
sidebar_position: 54
---

# Audiobookshelf

Self-hosted [Audiobookshelf](https://www.audiobookshelf.org/): audiobook and podcast
server with per-user playback progress.

Config: [services/prod/audiobookshelf/](https://github.com/IanCou/Hyades/tree/main/services/prod/audiobookshelf) · IP/LXC/route: [network.md](../network.md)

## Access posture

LAN/Tailscale only: no public DNS record or Cloudflare Tunnel ingress rule. Same
mechanism as [Cobalt](./cobalt#access-posture).

## Notes

- Libraries live on the LXC's local disk; bump `disk_size` in
  `terraform/envs/prod/main.tf` if they outgrow it.

## References

- [Audiobookshelf site](https://www.audiobookshelf.org/)
- [Audiobookshelf GitHub](https://github.com/advplyr/audiobookshelf)
