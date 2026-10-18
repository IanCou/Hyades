---
title: AdGuard Home
sidebar_position: 15
---

# AdGuard Home

Internal DNS resolver + ad filter; replaced Pi-hole. Reachable directly on the LAN;
Tailscale clients (including exit-node users) reach it via a DNS override pinned in the
Tailscale container's own compose file, not via MagicDNS.

Deployed with `ansible-playbook playbooks/adguard.yml`, not the standard `deploy.yml`.

Config: [services/core/adguard/](https://github.com/IanCou/Hyades/tree/main/services/core/adguard) · IP/LXC/route: [network.md](../network.md)

## Rewrite table

| Pattern                      | →                                      |
| ---------------------------- | -------------------------------------- |
| `*.example.com`              | `10.0.1.10` (Caddy)                    |
| `*.example.internal`         | direct LXC IPs (SSH)                   |
| `node1/2/3.example.internal` | `10.0.0.10/11/12` (overrides wildcard) |
| everything else              | upstream (NextDNS)                     |

## systemd-resolved conflict

Debian 12's `systemd-resolved` binds `:53`. `adguard.yml` detects this
via `service_facts`, disables the unit, and replaces `resolv.conf`
pre-flight. Without this, the container fails to bind.

## Tailscale integration

MagicDNS is deliberately **disabled** (`TS_ACCEPT_DNS=false`) on both
Tailscale nodes (see [Tailscale](./tailscale.md) for why). Instead, the
[Tailscale](./tailscale.md) and [gateways/tailscale](./raspberrypi-gateway.md)
containers each pin their own `dns:` block straight to this AdGuard instance
(with the Pi as fallback), so exit-node clients keep AdGuard filtering and
`*.example.internal` rewrites without depending on tailnet-wide DNS
settings at all.

## References

- [AdGuard Home wiki](https://github.com/AdguardTeam/AdGuardHome/wiki)
- [Tailscale split DNS](https://tailscale.com/kb/1054/dns)
