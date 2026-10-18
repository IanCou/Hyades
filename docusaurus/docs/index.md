---
slug: /
sidebar_position: 0
---

# Hyades Docs

Reference docs and runbooks for the homelab.

## Reference

- [Architecture](./architecture): repo layout, how a change ships end to end
- [Network](./network): subnets, DNS, reverse proxy (generated)
- [Hardware](./hardware): node specs
- [Proxmox](./proxmox): cluster, nodes, storage pools
- [Unprivileged LXC uid mapping](./unprivileged-lxc)
- [CI overview](./ci): the `ci.yml` jobs, what each one guards
- [Dev workflow](./dev-workflow): day-to-day operator workflow
- [Git flow & branch protection](./git-flow)

## Stack

### Core infra

- [Caddy](./stack/caddy): reverse proxy + cloudflared
- [AdGuard Home](./stack/adguard): internal DNS
- [Tailscale](./stack/tailscale): VPN + subnet router
- [Authentik](./stack/authentik): SSO
- [Portainer](./stack/portainer): Docker UI
- [Semaphore](./stack/semaphore): Ansible web UI
- [GitHub runner](./stack/github-runner): self-hosted CI/CD
- [Docs site](./stack/docs-site): this site
- [Jump host](./stack/jump): SSH bastion

### Monitoring

- [Prometheus](./stack/prometheus): metrics
- [Grafana](./stack/grafana): dashboards
- [Uptime Kuma](./stack/uptime-kuma): service uptime monitoring
- [Ntfy](./stack/ntfy): push notifications

### Prod apps

- [Immich](./stack/immich): photos
- [Nextcloud](./stack/nextcloud): files
- [Coolify](./stack/coolify): self-hosted PaaS
- [SearXNG](./stack/searxng): metasearch
- [AirTrail](./stack/airtrail): personal flight tracker
- [Cobalt](./stack/cobalt): media downloader
- [Kavita](./stack/kavita): ebook and manga library
- [Audiobookshelf](./stack/audiobookshelf): audiobook library
- [People Portal staging](./stack/peopleportal-staging): AppDev Club staging environment
- [Home Assistant](./stack/homeassistant): home automation
- [Speedtest Tracker](./stack/speedtest): scheduled speed tests

### Test / experimental

- [n8n](./stack/n8n): workflow automation
- [Kafka](./stack/kafka): event streaming
- [Internship Watcher](./stack/internship-watcher): job-posting scraper
- [OpenClaw](./stack/openclaw): AI gateway (Claude)
- [dev](./stack/dev): personal dev box

### Gateways

- [Raspberry Pi Gateway](./stack/raspberrypi-gateway): standalone AdGuard + Tailscale, survives a cluster power-off

## Runbooks

- [New service](./runbooks/new-service)
- [New LXC](./runbooks/new-lxc)
- [DNS and reverse proxy](./runbooks/dns-and-reverse-proxy)
- [Dry-run a deploy](./runbooks/dry-run-deploys)
- [Backup & restore](./runbooks/backup-restore)
- [Node failure](./runbooks/node-failure)
- [macOS VM on Proxmox (OpenCore)](./runbooks/macos-vm)
- [Arch VM](./runbooks/arch-vm)
- [Ubuntu VM](./runbooks/ubuntu-vm)
- [QEMU console automation](./runbooks/qemu-console-automation)
- [Update docs](./runbooks/update-docs)

## Decisions

[Architecture Decision Records](./decisions/): the trade-offs behind each
major design choice (LXC vs VM, Caddy vs NPM, tier placement, the self-hosted
runner's trust model, secrets, and more).

## Postmortems

Corrections of Error (incident write-ups): what broke, why, and what changed
as a result.

- [2026-07-14: Portainer stray git stack](./coe/2026-07-14-portainer-stray-git-stack)
- [2026-04-17: Nextcloud OIDC issuer mismatch](./coe/2026-04-17-nextcloud-oidc-issuer-mismatch)

## Changelog

Latest first:

- [2026-08-02: Home Assistant provisioned](./changelog/2026-08-02-homeassistant)
- [2026-07-25: Kavita + Audiobookshelf](./changelog/2026-07-25)
- [2026-07-19: cobalt web frontend, split from the API](./changelog/2026-07-19)
- [2026-07-18: cobalt.tools LXC (Tailscale/LAN only)](./changelog/2026-07-18)
- [2026-07-16: dev LXC + Windows11 re-provisioned](./changelog/2026-07-16)
- [2026-07-12: GitOps-managed Tailscale ACLs](./changelog/2026-07-12)
- [2026-07-06: Tailscale LXC resource bump](./changelog/2026-07-06)
- [2026-05-24: macOS Tahoe VM, cross-node migrations](./changelog/2026-05-24)
- [2026-04-17: Docs site](./changelog/2026-04-17)
