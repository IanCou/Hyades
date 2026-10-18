# 0002. Caddy over Nginx Proxy Manager for reverse proxy + TLS

**Status:** Accepted

## Context

Every web service is reached through one reverse proxy at `10.0.1.10` (LXC
111). It needs to terminate TLS for `*.example.com`, route to internal LXC
IPs, and integrate with the split-DNS scheme (`*.example.com` → Caddy,
`*.example.internal` → direct LXC). The whole repo is infrastructure-as-code
under version control, so the proxy config should live there too.

Because the services are internal-only, certificates must be issued via the
ACME **DNS-01** challenge against Cloudflare (HTTP-01 would require exposing port
80 publicly). A single wildcard cert for `*.example.com` is preferable to
per-host certs so adding a service needs no new certificate.

## Options considered

### Option A: Nginx Proxy Manager (NPM)

- **Pros:** Friendly web UI; easy for occasional changes; popular in homelabs.
- **Cons:** Config and certs live in a SQLite database and UI state, not in git;
  it falls outside the IaC model and isn't diffable or code-reviewable. DNS-01
  wildcard issuance is awkward; per-host certs are the common path. Restoring the
  proxy means restoring its DB, not re-applying a file.

### Option B: Raw Nginx + Certbot

- **Pros:** Maximum control; config is plain text in git.
- **Cons:** TLS automation is a separate moving part (Certbot timers, renewal
  hooks, reload glue). More boilerplate per vhost. DNS-01 wildcard setup is manual.

### Option C: Caddy with the Cloudflare DNS provider (chosen)

- **Pros:** A single `Caddyfile` (in `services/core/caddy/`, version-controlled and
  deployed by `playbooks/caddy.yml`) is the entire config, diffable and
  code-reviewed. Automatic ACME **DNS-01** wildcard issuance and renewal for
  `*.example.com` via the built-in Cloudflare module; one cert covers every
  current and future host. Adding a service is a few lines of Caddyfile, no
  certificate step. Implicit HTTPS by default.
- **Cons:** No UI: every change is a file edit plus a redeploy. The Cloudflare
  DNS plugin requires a custom Caddy build (a Dockerfile in the same dir).
  Caddyfile syntax is a smaller ecosystem to learn than Nginx's.

## Decision

Use Caddy with the Cloudflare DNS-01 plugin as the single reverse proxy, holding
one wildcard certificate for `*.example.com`. Configuration is the
`Caddyfile`, kept in git and deployed via Ansible.

The deciding factor is config-as-code with zero-touch wildcard TLS: it keeps the
proxy inside the same review-and-deploy pipeline as everything else and removes
certificate management as a recurring task.

## Consequences

### Positive

- Adding a service is a Caddyfile edit + `playbooks/caddy.yml` run: no
  certificate work, no UI clicking.
- One wildcard cert auto-renews; no per-host cert sprawl and no public port 80.
- Proxy config is diffable, reviewable, and restored by re-applying a file.

### Negative / risks

- No GUI; all changes go through file edits and a redeploy (acceptable for a
  single operator).
- DNS-01 depends on a Cloudflare API token with DNS edit rights, a credential to
  protect (see ADR [0006](./0006-sops-for-secrets.md)).
- Custom Caddy image must be rebuilt to update the Cloudflare plugin.

## Update (2026-10-18)

The current `services/core/caddy/Caddyfile` has one site block per host and
global `acme_dns cloudflare`. Caddy now obtains DNS-01 certificates for the
configured hosts individually; it does not use the wildcard certificate
described in the original decision.
