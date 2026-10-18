---
title: Uptime Kuma
sidebar_position: 30
---

# Uptime Kuma

Service uptime monitor with alerting. Watches all internal and external endpoints.

Config: [services/core/uptime-kuma/](https://github.com/IanCou/Hyades/tree/main/services/core/uptime-kuma) · IP/LXC/route: [network.md](../network.md)

## Monitors as code

Monitors are provisioned by `services/core/uptime-kuma/setup_monitors.py` using the
[`uptime-kuma-api`](https://github.com/lucasheld/uptime-kuma-api) Python wrapper; the
`MONITORS` list there is the source of truth. The playbook is idempotent (re-running
skips existing monitors):

```bash
cd ansible
ansible-playbook playbooks/uptime-kuma-monitors.yml
# Uptime Kuma login uses vault_uptime_kuma_username / vault_uptime_kuma_password;
# the ntfy notification uses vault_ntfy_username / vault_ntfy_password in group_vars/all/vault.yml.
```

To add a monitor, append to `MONITORS` and re-run the playbook. The personal website and
publicly tunneled services (Authentik, Immich, Nextcloud) are checked via their public
URLs; everything else by internal IP, with TLS verification skipped for self-signed
upstreams (Portainer, Proxmox). Ansible supplies the Kuma password through its environment
and suppresses command output in logs.

## Alerting

`setup_monitors.py` also provisions the notification channel as code: an
`Ntfy: homelab` notification (publishing to [ntfy](./ntfy.md)'s `homelab` topic) is
created and applied to every monitor automatically; no manual Settings → Notifications
step needed.
The ntfy credentials are passed separately from the Uptime Kuma login. The notification
is only created if absent, so changing ntfy credentials later requires editing or
deleting the existing notification in the UI.

## References

- [Uptime Kuma GitHub](https://github.com/louislam/uptime-kuma)
- [uptime-kuma-api](https://github.com/lucasheld/uptime-kuma-api)

Existing ntfy notification settings are reconciled in place, including rotated
credentials. Unchanged settings are skipped; updating a notification preserves
its ID and monitor assignments.
