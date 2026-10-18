---
title: Tailscale
sidebar_position: 20
---

# Tailscale

VPN: subnet router advertising `10.0.0.0/22` and `fd00:db8::/64` plus an exit node. It's how every
LAN-only service in the lab is reached remotely (see [Cobalt](./cobalt#access-posture)).
The [Raspberry Pi gateway](./raspberrypi-gateway.md) is a second subnet router advertising
identical routes for HA failover.

Config: [services/core/tailscale/](https://github.com/IanCou/Hyades/tree/main/services/core/tailscale) · IP/LXC/route: [network.md](../network.md)

## Version pin

LXC 116 uses `tailscale/tailscale:v1.104.1`, the newest stable `vX.Y.Z` tag from Docker
Hub's tags API when pinned. Bump it deliberately via PR: merging redeploys the primary
subnet router and exit node, so merge from the LAN or while the Pi carries the routes.
The Pi uses the native apt package with Tailscale auto-update enabled (check and apply),
so it tracks stable independently.

## Unprivileged LXC quirk

Tailscale needs `/dev/net/tun`. Add to `/etc/pve/lxc/116.conf`:

```
lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
```

Automated by `ansible-playbook playbooks/tailscale-postprovision.yml`; run it after
provisioning. Without it, the container starts but `tailscale up` fails with "cannot open
/dev/net/tun".

## Subnet + DNS

- Subnet routes and exit-node are auto-approved via `autoApprovers` in `policy.hujson`
  for devices tagged `tag:homelab-gateway`; no manual admin-UI approval once tagged.
- MagicDNS is off in the tailnet admin console; `TS_ACCEPT_DNS=false` separately stops
  the LXC node from accepting tailnet DNS settings. The admin-console DNS nameservers
  are the Pi (`10.0.0.3`) first, then AdGuard (`10.0.1.16`). Tailscale makes the exit
  node the resolver for any client using it, which would otherwise mean the container's
  own `resolv.conf` (ISP default) decides what exit-node clients get, bypassing
  [AdGuard](./adguard.md) entirely, no filtering, no `*.example.internal` rewrites.
  Instead, the compose file's `dns:` block pins the container's resolver to AdGuard
  (`10.0.1.16`, then the Pi at `10.0.0.3` as fallback), so exit-node clients keep
  AdGuard regardless of the tailnet's MagicDNS settings.
- After applying `raspberrypi-setup.yml` on the Pi exit node, the host's `resolv.conf`
  uses loopback AdGuard (`127.0.0.1`) first, then `1.1.1.1` as fallback. Its openresolv configuration keeps loopback first
  when dhcpcd regenerates the file.

## ACL policy (GitOps-managed)

The tailnet ACL policy is version-controlled: [`policy.hujson`](https://github.com/IanCou/Hyades/blob/main/policy.hujson)
at the repo root, synced by [`.github/workflows/tailscale-acl.yml`](https://github.com/IanCou/Hyades/blob/main/.github/workflows/tailscale-acl.yml)
via `tailscale/gitops-acl-action`, validated on every PR that touches it, applied on
merge to `main`. **Do not hand-edit the policy in the admin console**; the next merge
overwrites it. It scopes subnet-route (LAN) access to `tag:homelab-admin` devices while
keeping exit-node routing for everyone; see
[ADR 0007](../decisions/0007-tailscale-acl-route-scoping.md).

## References

- [Subnet routers](https://tailscale.com/kb/1019/subnets)
- [Tailscale in containers](https://tailscale.com/kb/1282/docker)
- [GitOps for Tailscale ACLs](https://tailscale.com/kb/1306/gitops-acls-github)
