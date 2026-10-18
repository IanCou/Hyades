---
title: OpenClaw
sidebar_position: 50
---

# OpenClaw

Self-hosted [OpenClaw](https://www.npmjs.com/package/openclaw) AI gateway, configured
**claude-only** (Claude Sonnet + Opus) through a single provider, `anthropic`: the Claude
API (`https://api.anthropic.com`, `anthropic-messages`) with an API key supplied through
the environment.

Deployed as a built image (`Dockerfile`) via `ansible-playbook playbooks/openclaw.yml`
(bespoke, not `deploy.yml`).

Config: [services/test/openclaw/](https://github.com/IanCou/Hyades/tree/main/services/test/openclaw) · IP/LXC/route: [network.md](../network.md)

## Access posture

LAN/Tailscale only: **no public tunnel**, because the gateway spends from a personal API
key. Same mechanism as [Cobalt](./cobalt#access-posture).

## Config

The committed
[`openclaw.json`](https://github.com/IanCou/Hyades/blob/main/services/test/openclaw/openclaw.json)
is baked into the image and carries no secrets; change it and rebuild. It declares the
`anthropic` provider with the Claude Sonnet and Opus models and references the key as
`${ANTHROPIC_API_KEY}`.

## Auth

The API key lives in the service's gitignored `.env` as `ANTHROPIC_API_KEY` (see
`.env.example`), alongside `OPENCLAW_GATEWAY_TOKEN`. `make push-secret service=openclaw`
copies it to the runner, `playbooks/openclaw.yml` fails fast if it is empty, and
`docker-compose.yml` passes it into the container as an environment variable. No login
step is needed after deploy. To rotate the key, update `.env`, push it, and redeploy.

The gateway token is the only thing in front of the gateway, so keep it strong
(`openssl rand -hex 32`). The `openclaw-state` volume holds gateway state. The container
runs as `node:22-slim`'s built-in uid-1000 `node` user, not root.

## Provisioning runbook

After first provisioning, config changes under `services/test/openclaw/` redeploy
automatically via CI's `deploy` job (it picks up `playbooks/openclaw.yml`). To
(re-)provision from scratch:

```bash
# 1. Create the LXC
terraform -chdir=terraform/envs/test apply -target=module.openclaw
ansible-playbook ansible/playbooks/docker.yml -l openclaw

# 2. Redeploy Caddy and add the AdGuard rewrite (idempotent, derived from Terraform + Caddyfile)
ansible-playbook ansible/playbooks/caddy.yml
ansible-playbook ansible/playbooks/adguard-rewrites.yml -e adguard_password=<pass>

# 3. Push secrets (gateway token + Anthropic API key), then deploy (builds the image)
make push-secret service=openclaw
ansible-playbook ansible/playbooks/openclaw.yml

# 4. Host metrics + scrape target
ansible-playbook ansible/playbooks/node-exporter.yml -l openclaw
ansible-playbook ansible/playbooks/prometheus.yml

# 5. Confirm it's up
make verify service=openclaw url=https://openclaw.example.com
```

Optionally run `docker exec openclaw openclaw doctor` afterward to repair/fill config
defaults.

## References

- [OpenClaw on npm](https://www.npmjs.com/package/openclaw)
