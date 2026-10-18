---
title: Portainer
sidebar_position: 25
---

# Portainer

Docker management UI. Agents run on every other Docker LXC and register back to this
instance. Login is Portainer's own native Authentik OIDC, so it's deliberately excluded
from Caddy's forward-auth gate (see [Authentik](./authentik.md)).

Config: [services/core/portainer/](https://github.com/IanCou/Hyades/tree/main/services/core/portainer) · IP/LXC/route: [network.md](../network.md)

See also the [stray git stack COE](../coe/2026-07-14-portainer-stray-git-stack.md).

## Self-signed upstream

Portainer serves `:9443` with a self-signed cert, so Caddy proxies it with
`transport http { tls_insecure_skip_verify }`.

## Agents

`ansible-playbook playbooks/portainer-agent.yml -l <host>` deploys `portainer/agent:lts`
on a target LXC and calls the Portainer API to register the environment. Credentials come
from `vault_portainer_user` / `vault_portainer_password`.

## References

- [Portainer Docker install](https://docs.portainer.io/start/install-ce/server/docker)
- [Portainer Edge agent](https://docs.portainer.io/admin/environments/add/docker/agent)
