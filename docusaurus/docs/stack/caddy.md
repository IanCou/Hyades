---
title: Caddy
sidebar_position: 10
---

# Caddy

Reverse proxy for all `*.example.com` web UIs; replaced Nginx Proxy Manager
([ADR 0002](../decisions/0002-caddy-over-nginx-proxy-manager.md)). Colocated with
cloudflared (tunnel) on the same LXC.

Deployed with `ansible-playbook playbooks/caddy.yml`, not the standard `deploy.yml`.

Config: [services/core/caddy/](https://github.com/IanCou/Hyades/tree/main/services/core/caddy) · IP/LXC/route: [network.md](../network.md)

## Custom build

`services/core/caddy/Dockerfile` uses `caddy:2-builder` + xcaddy to bake in
`caddy-dns/cloudflare`. DNS-01 means cert issuance works even for local-only
subdomains (no public reachability required).

## Deploy pattern

Unlike generic `deploy.yml`, `caddy.yml` syncs the **whole** service dir
(Caddyfile + Dockerfile + compose + .env) because the image is built
from source. `docker_compose_v2` runs with `build: always`.

## Caddyfile quirks

- Global `acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}`: all domains use DNS-01.
- Self-signed upstreams (Proxmox, Portainer) use
  `transport http { tls_insecure_skip_verify }`.
- Cloudflare token lives in `services/core/caddy/.env` (Zone:DNS:Edit scope, not in git).

## Adding a new subdomain

1. Ensure the DNS name exists in the Cloudflare zone (any record; the
   tunnel handles the actual routing, or AdGuard does internally).
2. Add a block to `services/core/caddy/Caddyfile`.
3. `ansible-playbook playbooks/caddy.yml`.
4. Cert issues in ~10–15s via DNS-01.

## cloudflared

Installed on the same LXC via `ansible/roles/cloudflared/`, token stored as
`vault_cloudflare_tunnel_token`. Public `*.example.com` routes terminate at Caddy
locally; which hostnames are public is set by the tunnel's ingress rules in Cloudflare's
dashboard, not by this repo (see [Cobalt](./cobalt#access-posture)).

## References

- [Caddyfile reference](https://caddyserver.com/docs/caddyfile)
- [xcaddy](https://github.com/caddyserver/xcaddy)
- [caddy-dns/cloudflare](https://github.com/caddy-dns/cloudflare)
