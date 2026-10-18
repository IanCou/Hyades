---
title: "2026-10-18: Apply Pi exit-node DNS configuration"
sidebar_position: 0
---

# 2026-10-18: Apply Pi exit-node DNS configuration

Applied `ansible/playbooks/raspberrypi-setup.yml` to the Raspberry Pi gateway.
The initial full run completed with `ok=11 changed=3 failed=0`.

Verification caught an openresolv behavior: when a local resolver is configured,
its default `resolv_conf_local_only` setting omits non-local resolvers, including
an explicitly configured public fallback. The installed `resolvconf.conf(5)`
manual documents setting this to `NO` to retain fallback resolvers.

The playbook now persists `name_servers="127.0.0.1 1.1.1.1"` together with
`resolv_conf_local_only=NO`. Its generated-file check also requires both resolver
entries in that order, so a missing fallback is repaired rather than skipped.
The DNS tasks were reapplied after this correction.

The gateway stack page and agent guidance record this regeneration behavior.
No IP addresses, subnet advertisements, or Tailscale acceptance settings changed.

Verification after reapplying the corrected DNS tasks (`ok=7 changed=3 failed=0`):

- `/etc/resolv.conf` contains `127.0.0.1`, then `1.1.1.1`.
- A second `resolvconf -u` leaves the generated file unchanged with both entries.
- Public DNS and `caddy.example.internal` resolve through `127.0.0.1`.
- The public fallback answers a direct query.
- Tailscale is running without health errors and still advertises both LAN subnet
  routes and exit-node routes.
