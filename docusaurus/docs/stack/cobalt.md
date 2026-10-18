---
title: Cobalt
sidebar_position: 52
---

# Cobalt

Self-hosted [cobalt](https://cobalt.tools/): turns links from YouTube, Twitter/X,
TikTok, Instagram, Reddit, etc. into direct file downloads without ads or tracking. Runs
both the API and the official web frontend, same split as upstream's `cobalt.tools` /
`api.cobalt.tools`.

Deployed with the dedicated `ansible-playbook playbooks/cobalt.yml`, not `deploy.yml`
(see below).

Config: [services/prod/cobalt/](https://github.com/IanCou/Hyades/tree/main/services/prod/cobalt) · IP/LXC/route: [network.md](../network.md)

## Why the frontend needs its own Dockerfile

Upstream ships **no Docker image for the web frontend**; it's a SvelteKit app built with
`@sveltejs/adapter-static` and deployed by upstream to Cloudflare Pages. Since the output
is plain static files, [`Dockerfile.web`](https://github.com/IanCou/Hyades/blob/main/services/prod/cobalt/Dockerfile.web)
clones the cobalt monorepo at a **pinned commit** (matching the API image's version, so
frontend and API never drift), runs the pnpm workspace build, and serves the output via
nginx. Because it's a source build, it's deployed by `cobalt.yml` (mirrors `caddy.yml`'s
pattern for services with a custom `Dockerfile`); the generic `deploy.yml` only syncs
`docker-compose.yml` + `.env`, not a build context.

## Gotchas

- `WEB_DEFAULT_API` / `WEB_HOST` are **build-time** env vars, baked into the JS bundle;
  changing them needs a rebuild, not a restart. `WEB_DEFAULT_API` holds the same value as
  `API_URL` but is kept separate because they're consumed by different containers at
  different times.
- `API_URL` must match how the API is actually accessed or tunnel/proxy downloads break.
- Watchtower uses the `nickfedor/watchtower` fork: `containrrr/watchtower` in upstream's
  example is unmaintained and its client is too old for this host's Engine. It only
  updates the `cobalt` API image; `cobalt-web` isn't a pulled image.
- Upstream's many optional API env vars (rate limits, cookies, Turnstile, YouTube session
  handling; [reference](https://github.com/imputnet/cobalt/blob/main/docs/api-env-variables.md))
  are left unset; defaults are fine for a private single-user instance.
- The frontend build (pnpm install + Vite/Rollup across the whole workspace) needs real
  headroom on the LXC; it was bumped up from an initial API-only sizing for this.
- Both API and frontend are stateless (no volumes, no DB); upgrades are just a redeploy.

## Access posture

This is the canonical explanation for every LAN/Tailscale-only service
([AirTrail](./airtrail), [Kavita](./kavita), [Audiobookshelf](./audiobookshelf),
[Home Assistant](./homeassistant), …).

Both `cobalt.example.com` and `api.cobalt.example.com` are fronted by Caddy with
a real TLS cert (wildcard `*.example.com` via DNS-01), but **neither is reachable from
the public internet**. Public reachability is gated by the **Cloudflare Tunnel**
(`cloudflared`, on the Caddy LXC) whose ingress hostnames are configured in Cloudflare's
dashboard, outside this repo, not by whether a Caddy block exists. Neither cobalt
hostname has been added there, and neither has a public DNS record (`dig
cobalt.example.com @1.1.1.1` returns nothing, vs. a genuinely public service like
`immich.example.com`, which resolves to Cloudflare's edge IPs).

- **AdGuard rewrites** (internal split-DNS only): both hostnames → `10.0.1.10`
  (Caddy). Reachable from the LAN and from any device on the Tailscale subnet router
  (advertises `10.0.0.0/22`).
- `<svc>.example.internal` also exists (auto-derived from the Terraform module),
  pointing straight at the LXC's own IP, for SSH/direct access, bypassing Caddy.
- To make a service public later, the Caddy config is already correct; the only extra
  steps are adding the hostname(s) to the Cloudflare Tunnel's ingress rules and public
  DNS.

## References

- [cobalt.tools](https://cobalt.tools/)
- [cobalt GitHub](https://github.com/imputnet/cobalt)
- [Run-an-instance docs](https://github.com/imputnet/cobalt/blob/main/docs/run-an-instance.md)
- [cobalt web README](https://github.com/imputnet/cobalt/blob/main/web/README.md)
