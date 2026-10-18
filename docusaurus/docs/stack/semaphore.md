---
title: Semaphore
sidebar_position: 40
---

# Semaphore

Web UI for running Ansible playbooks: wraps the existing playbook repo with a UI, RBAC,
and run history. Sits behind Caddy's Authentik forward-auth gate (see
[Authentik](./authentik.md)).

Config: [services/core/semaphore/](https://github.com/IanCou/Hyades/tree/main/services/core/semaphore) · IP/LXC/route: [network.md](../network.md)

## Setup

1. Add the playbook repo as a **Repository** (SSH key or HTTPS token).
2. Add an **Inventory** pointing at your `hosts` file.
3. Add an **Environment** with the Ansible Vault password: store
   `ANSIBLE_VAULT_PASSWORD` as a key store secret so `ansible-vault` playbooks decrypt
   without prompting.
4. Create **Task Templates** for each playbook, one per service.

## References

- [Semaphore docs](https://docs.semaphoreui.com/)
- [Semaphore GitHub](https://github.com/semaphoreui/semaphore)
