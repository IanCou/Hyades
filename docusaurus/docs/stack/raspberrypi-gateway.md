---
title: Raspberry Pi Gateway
sidebar_position: 48
---

# Raspberry Pi Gateway

An always-on Raspberry Pi (bare metal, not an LXC; user `chaff`, inventory tier
`gateways`) that runs a **standalone AdGuard + Tailscale** outside the Proxmox cluster,
so DNS and remote access survive a full cluster power-off, and can wake the cluster back
up over the network. See [ADR 0004: Split DNS with a Pi secondary](../decisions/0004-split-dns-with-pi-secondary.md).

Set up with `ansible-playbook playbooks/raspberrypi-setup.yml`, plus the AdGuard compose
stack under [`services/gateways/`](https://github.com/IanCou/Hyades/tree/main/services/gateways).
Tailscale is a native apt package, not compose (see below). Its full command is in
[raspberrypi-setup.md](https://github.com/IanCou/Hyades/blob/main/services/core/tailscale/raspberrypi-setup.md).

IP: [network.md](../network.md)

## Why it exists

AdGuard and Tailscale normally run as core LXCs on `node1`. If `node1` or the whole
cluster is down, internal DNS and the VPN go with it, a circular dependency when you're
trying to fix the cluster remotely. The Pi is a second, independent copy that keeps
resolving names and routing the tailnet while the cluster is off.

## What runs on it

- **AdGuard Home**: compose, `network_mode: host`, config/work under `/data/adguard`.
- **node_exporter**: scraped by Prometheus like every other host.
- **Tailscale**: native apt package (`pkgs.tailscale.com/stable/raspbian`), **not**
  Docker. Hostname `raspberrypi`, tagged `tag:homelab-gateway`:
  `sudo tailscale up --advertise-exit-node --advertise-routes=10.0.0.0/22,fd00:db8::/64 --advertise-tags=tag:homelab-gateway --accept-routes=false --accept-dns=false`.
  These routes must match LXC 116 exactly for HA failover. The apt package auto-updates;
  unlike LXC 116's container image, it is not pinned.
- **Exit-node DNS**: the Pi's `resolv.conf` uses `127.0.0.1` (its AdGuard) first,
  then `1.1.1.1` as fallback. `raspberrypi-setup.yml` persists both addresses in
  openresolv as `name_servers="127.0.0.1 1.1.1.1"`, with
  `resolv_conf_local_only=NO`. Without the latter setting, openresolv suppresses
  public fallback resolvers whenever a local resolver is present. Editing the
  generated `resolv.conf` alone does not survive `resolvconf -u`.

### Why Tailscale isn't in Docker

There used to be a `services/gateways/tailscale/docker-compose.yml`, deleted 2026-07
after discovering it had never once run successfully. The official `tailscale/tailscale`
image has never published an `arm/v6` build, and this Pi is genuine `armv6l` hardware
(`dpkg --print-architecture` = `armhf`; image manifests checked back to v1.32.3: none
had arm/v6). The container SIGILL-crash-looped from creation, leaving `/data/tailscale`
permanently empty. All along, the _actual_ working gateway was the separate native
install; the two ran in parallel, undetected, until an IPv6-routing change surfaced the
dead one.

## Wake-on-LAN

`raspberrypi-setup.yml` also enables kernel IP forwarding (for subnet routing), installs
`wakeonlan`, and sets up a `wake-homelab` script keyed to each node's MAC address. This
lets the Pi **power the cluster back on** after a shutdown, the reason it's safe to fully
power down Proxmox. Override the MACs at runtime:

```bash
ansible-playbook playbooks/raspberrypi-setup.yml \
  -e "node1_mac=AA:BB:CC:DD:EE:10 node2_mac=AA:BB:CC:DD:EE:11 node3_mac=AA:BB:CC:DD:EE:12"
```

## References

- [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome)
- [Tailscale subnet routers](https://tailscale.com/kb/1019/subnets)
- [Wake-on-LAN](https://wiki.archlinux.org/title/Wake-on-LAN)
