---
title: Nextcloud
sidebar_position: 40
---

# Nextcloud

File sync. Three-container stack (app + MariaDB + cron). User data lives on the NAS
(`10.0.0.249:/volume1/Ian/nextcloud` → `/mnt/nas/nextcloud` → container
`/var/www/html/data`); config and DB stay on the LXC rootfs for fast local storage.

Config: [services/prod/nextcloud/](https://github.com/IanCou/Hyades/tree/main/services/prod/nextcloud) · IP/LXC/route: [network.md](../network.md)

Note the app is served on `:8080`, **not** `:80`. See also the
[OIDC issuer mismatch COE](../coe/2026-04-17-nextcloud-oidc-issuer-mismatch.md).

## NAS permissions: the gotcha

The data dir must be **owned by host uid 100033:100033** (not 33:33) because the LXC is
unprivileged. Inside the container, www-data is uid 33, which maps to host uid 100033.
Run on the Proxmox host:

```bash
chown -R 100033:100033 /mnt/nas/nextcloud
```

Symptom when it's wrong:

> Your data directory is invalid. Ensure there is a file called ".ncdata"…
> Your data directory is not writable.

See [Unprivileged LXC uid mapping](../unprivileged-lxc.md) for the full picture.

## Secrets

DB passwords live in the gitignored `services/prod/nextcloud/.env` (template:
`.env.example`). Before deploying this compose change through CI, stage the file on
the runner with `ansible-playbook playbooks/push-secret.yml -e service=nextcloud`
from `ansible/`; compose now refuses to start without it.

The compose file previously committed the DB password `password`. If the live MariaDB
root or nextcloud user password is still `password`, rotate it with `ALTER USER` in
MariaDB, update `dbpassword` in Nextcloud's `config.php`, then set the new values in
`.env`.

## References

- [Nextcloud Docker image](https://hub.docker.com/_/nextcloud)
- [Nextcloud admin: data dir permissions](https://docs.nextcloud.com/server/latest/admin_manual/installation/installation_wizard.html#data-directory-location)
