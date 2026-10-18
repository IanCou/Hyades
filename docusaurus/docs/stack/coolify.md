---
title: Coolify
sidebar_position: 45
---

# Coolify

Self-hosted PaaS (Heroku/Netlify alternative): a second deployment plane alongside the
main Terraform + Ansible IaC.

Config: [services/test/coolify/](https://github.com/IanCou/Hyades/tree/main/services/test/coolify) · IP/LXC/route: [network.md](../network.md)

## Second deployment plane

Coolify is not the usual Docker Compose stack. It runs its own installer
(`coolify`, `coolify-db`, `coolify-redis`, `coolify-realtime`, `coolify-proxy`)
and then hosts/deploys further apps (e.g. `actual-budget`) from its own UI.
Those managed apps live **outside** the main IaC; they are defined inside
Coolify, not under `services/`.

## Access posture

Login is Coolify's own native Authentik OIDC, so it is deliberately excluded from
Caddy's forward-auth gate (see [Authentik](./authentik#forward-auth-caddy-gate)).

## Initial admin

Change the root admin email after install:

```bash
docker exec -ti coolify sh -c "php artisan root:change-email"
```

See [`services/test/coolify/setup.md`](https://github.com/IanCou/Hyades/blob/main/services/test/coolify/setup.md).

## Cloudflared tunnel

Coolify-managed apps are exposed through their own Cloudflare tunnel terminated by
Coolify's Traefik proxy, not the cluster Caddy:

```bash
ansible-playbook playbooks/cloudflared-coolify.yml
```

Applies the `cloudflared` role on the `coolify` host; requires
`vault_cloudflare_coolify_tunnel_token` in `group_vars/all/vault.yml`.

## Migration playbook

Coolify was migrated from the old `test-services` VM (vmid 300) to this LXC via
[`ansible/playbooks/migrate-coolify.yml`](https://github.com/IanCou/Hyades/blob/main/ansible/playbooks/migrate-coolify.yml)
(requires the LXC to exist from `terraform apply` in `terraform/envs/prod` first). It
bootstraps Docker + the official Coolify installer, `pg_dump`s `coolify-db` and tars
`/data/coolify` on the old VM, copies both to the new LXC via the controller, restores
them, and runs `docker compose up -d` in `/data/coolify/source`.

## References

- [Coolify docs](https://coolify.io/docs)
- [Coolify GitHub](https://github.com/coollabsio/coolify)
- [cloudflared docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
