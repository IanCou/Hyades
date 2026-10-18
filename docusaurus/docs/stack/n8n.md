---
title: n8n
sidebar_position: 45
---

# n8n

Self-hosted workflow automation: event-driven and scheduled automations with a visual
node editor.

Config: [services/test/n8n/](https://github.com/IanCou/Hyades/tree/main/services/test/n8n) · IP/LXC/route: [network.md](../network.md)

## Gotchas

- `N8N_HOST` / `WEBHOOK_URL` are derived from `SUBDOMAIN` + `DOMAIN_NAME`, so production
  webhook URLs resolve to `https://n8n.example.com/` and external services can call
  workflow webhook triggers directly through Caddy.
- `N8N_PROTOCOL=http`: TLS is terminated upstream by Caddy; n8n itself serves plain
  HTTP.
- **Back up `/home/n8n/data` before any rebuild**: it holds the encryption key required
  to decrypt stored credentials (alongside the SQLite DB and workflows).

## References

- [n8n docs](https://docs.n8n.io/)
- [Environment variables reference](https://docs.n8n.io/hosting/configuration/environment-variables/)
- [Docker self-hosting guide](https://docs.n8n.io/hosting/installation/docker/)
