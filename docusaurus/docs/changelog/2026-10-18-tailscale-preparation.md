---
title: "2026-10-18: Prepare Tailscale and Pi DNS updates"
sidebar_position: 1
---

# 2026-10-18: Prepare Tailscale and Pi DNS updates

Pinned the primary Tailscale container to `v1.104.1` and prepared the Pi resolver
configuration to prefer its local AdGuard. Updated the route and DNS documentation
to distinguish the desired configuration from changes awaiting deployment.

Preflight checks confirmed that Pi AdGuard answers public DNS and the internal
Caddy SSH rewrite on loopback, and the Pi advertises both LAN subnet routes and
an exit node. The runner reaches both gateways directly over Ethernet. The pinned
container manifest exists and its compose file validates on the primary gateway.

The Pi DNS configuration has not been applied, and the primary router has not
been redeployed. The shared runner deployment fix landed in PR #65 during preparation. Apply the
Pi setup playbook separately after merging and verify DNS again.

The live dry run found a stale `systemd-resolved.service` fact with status
`not-found`. The playbook now skips that absent service instead of attempting to
disable it and failing before the DNS tasks.
