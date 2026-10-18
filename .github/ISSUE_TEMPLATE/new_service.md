---
name: New service
about: Stand up a new self-hosted service
title: "[service] "
labels: service
---

## Service

<!-- Name + one line on what it does and why you want it -->

## Tier

- [ ] `core`: edge / infra the rest depends on
- [ ] `prod`: daily-driver service
- [ ] `test`: kicking the tires

## Placement

- Target host / LXC: <!-- existing LXC, or "new LXC needed" -->
- Image(s): <!-- e.g. ghcr.io/owner/app:tag -->
- Needs persistent storage: <!-- yes/no (volumes, dataset, bind mount) -->

## Networking

- [ ] Reverse-proxied via Caddy (hostname: `__________.example.com`)
- [ ] Behind Authentik SSO
- [ ] Tailscale-only / not public
- Ports:

## Dependencies & secrets

<!-- DB, other services, API keys. Note which secrets go in the runner-local
`.env` and which (if any) in Ansible vault. -->

## Done when

- [ ] `docker-compose.yml` under `services/<tier>/<name>/`
- [ ] Deploy playbook wired up (generic `deploy.yml` or a `<name>.yml`)
- [ ] Caddy route + DNS if exposed
- [ ] Stack page added under `docusaurus/docs/stack/`
