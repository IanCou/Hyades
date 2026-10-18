---
title: Home Assistant
sidebar_position: 56
---

# Home Assistant

Self-hosted [Home Assistant](https://www.home-assistant.io/): home automation hub for
LAN and cloud-backed smart-home devices.

**First-run onboarding not yet completed**: visit `https://homeassistant.example.com`
(or `http://10.0.2.22:8123` directly) to create the admin account and finish setup.

Config: [services/prod/homeassistant/](https://github.com/IanCou/Hyades/tree/main/services/prod/homeassistant) · IP/LXC/route: [network.md](../network.md)

## Networking: `network_mode: host`, deliberate exception to this repo's norm

Every other stack runs on Docker's default bridge network with a single port mapping.
Home Assistant runs with `network_mode: host` instead, a deliberate exception.

Multicast/broadcast discovery protocols (mDNS, SSDP) that most LAN smart-home
integrations rely on (Sonos, Chromecast, Philips Hue, ESPHome, Shelly, HomeKit Bridge)
don't cross Docker's bridge NAT. Host networking is Home Assistant's own recommended
deployment mode for exactly this reason. The trade-off: the container shares the LXC's
network namespace instead of being isolated behind NAT, acceptable since the LXC is
dedicated to this one service.

Alternatives considered and rejected for now:

- **Bridge + `ports: ["8123:8123"]`**: consistent with every other service, but breaks
  device auto-discovery and HomeKit Bridge entirely.
- **macvlan**: gets discovery working with real isolation, at the cost of a dedicated
  LAN IP outside the tier's `/22` scheme, a host-to-macvlan-child communication quirk
  that needs a shim interface, and possibly enabling promiscuous mode on the LXC's vNIC
  at the Proxmox level. Revisit if isolation becomes a real requirement.

## Access posture

LAN/Tailscale only: no public DNS record or Cloudflare Tunnel ingress rule. Same
mechanism as [Cobalt](./cobalt#access-posture).

## Notes

- `trusted_proxies` is configured (`configuration.yaml` on the LXC has
  `use_x_forwarded_for: true` / `trusted_proxies: [10.0.1.10]`), required for the
  URL to work through Caddy.
- `.env` is staged on the CI runner via `push-secret.yml`, so CI-triggered redeploys
  keep it.
- USB device passthrough (Zigbee/Z-Wave dongles) is not configured; add a `devices:`
  bind and `privileged: true` (or a narrower cgroup rule) to the compose file if a radio
  stick gets attached to node3.
- If the recorder/history DB or add-ons need more headroom, bump `memory` in
  `terraform/envs/prod/main.tf`.
- Not yet added to the Proxmox backup job.

## References

- [Home Assistant site](https://www.home-assistant.io/)
- [Home Assistant Docker install docs](https://www.home-assistant.io/installation/linux#docker-compose)
