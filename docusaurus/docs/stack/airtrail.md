---
title: AirTrail
sidebar_position: 51
---

# AirTrail

Self-hosted [AirTrail](https://airtrail.johan.ohly.dk/) personal flight tracker that keeps
flight history off third-party services.

Config: [services/prod/airtrail/](https://github.com/IanCou/Hyades/tree/main/services/prod/airtrail) · IP/LXC/route: [network.md](../network.md)

## Access posture

LAN/Tailscale only: no Cloudflare Tunnel route or public DNS record (personal flight
data). Same mechanism as [Cobalt](./cobalt#access-posture).

## Gotchas

- `DB_PASSWORD` must be **alphanumeric only**; upstream docs warn special characters
  break the `DB_URL` connection string parsing.
- `DB_URL` isn't set in `.env`; the compose file builds it from `DB_USERNAME`,
  `DB_PASSWORD`, and `DB_DATABASE_NAME`, so there's one password to generate, not two
  places to keep in sync.

## First-run setup

No CLI/env-based admin bootstrap. After the stack is up, visit
`https://airtrail.example.com` and create the first account through the web UI
(AirTrail's [post-installation docs](https://airtrail.johan.ohly.dk/docs/install/post-installation)).

## References

- [AirTrail site](https://airtrail.johan.ohly.dk/)
- [AirTrail GitHub](https://github.com/JohanOhly/AirTrail)
