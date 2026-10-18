---
title: Authentik
sidebar_position: 30
---

# Authentik

SSO / identity provider for the lab's admin UIs.

Config: [services/core/authentik/](https://github.com/IanCou/Hyades/tree/main/services/core/authentik) · IP/LXC/route: [network.md](../network.md)

## Forward-auth (Caddy gate)

`services/core/caddy/Caddyfile` has an `(authentik)` snippet wired into
AdGuard/Grafana/Semaphore's site blocks via `import authentik`, pointing at
Authentik's embedded outpost (`/outpost.goauthentik.io/auth/caddy`).
**Portainer and Coolify are deliberately excluded**: both already have
their own native Authentik OIDC login configured as applications, and
layering forward_auth on top would intercept requests before that login is
ever reached.

Proxy Providers (forward auth, single application mode) exist in Authentik
for all three protected domains, bound to the embedded outpost; an
unauthenticated request to the outpost's `/auth/caddy` path correctly
302-redirects into Authentik's OAuth flow.

Outpost gotcha (fixed): the embedded outpost's `authentik_host` config
(`Outposts` → embedded outpost → `config`) was stale, pointing at
`10.0.0.20:9000`, an old legacy VM IP. Fixed to `10.0.1.11:9000`, with
`authentik_host_browser` set to `https://auth.example.com`.

## Known unresolved bug (2026-07-13)

Despite `authentik_host_browser` being correctly set, the embedded outpost still
redirects unauthenticated requests straight to `authentik_host`
(`http://10.0.1.11:9000/...`). Verified live against `grafana.example.com`;
container restart + outpost config resave changed nothing. This is a documented
upstream limitation: the embedded outpost's initial forward-auth redirect never
consults `authentik_host_browser` for the OAuth `/application/o/authorize/` hop
([goauthentik/authentik#5922](https://github.com/goauthentik/authentik/issues/5922),
closed wontfix; [#12738](https://github.com/goauthentik/authentik/issues/12738)).
Net effect: anyone hitting a protected app (grafana/adguard/semaphore) from outside the
LAN while unauthenticated gets redirected to an internal IP their browser can't reach.

Planned fix (not yet applied; needs a compose edit + redeploy + outpost UI change):
point `authentik_host` itself at `https://auth.example.com`. Caveat: the Authentik
LXC's DNS resolver is the ISP's, not AdGuard, so `auth.example.com` resolves there
to Cloudflare's public IPs; flipping `authentik_host` naively would hairpin the
outpost's internal API traffic out through the internet and back through the tunnel.
Safe version: first add a Docker `extra_hosts` entry in
`services/core/authentik/docker-compose.yml` pinning `auth.example.com` → Caddy's
LAN IP (`10.0.1.10`) for the authentik containers, so outpost↔core traffic stays
LAN-local (Caddy already holds a real cert for that domain via DNS-01).

## References

- [Authentik docs](https://goauthentik.io/docs/)
- [Authentik docker-compose](https://goauthentik.io/docs/installation/docker-compose)
