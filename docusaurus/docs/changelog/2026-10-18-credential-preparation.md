---
title: "2026-10-18: Prepare credential migration"
sidebar_position: 4
---

# 2026-10-18: Prepare credential migration

Moved service credentials into environment variables and encrypted vault variables.
The local vault now includes the AdGuard and Uptime Kuma usernames and verified
ntfy credentials. Nextcloud's local and runner `.env` files match its existing
stored compose and application configuration; no secret values are committed.

Uptime Kuma now reconciles existing notification credentials in place, preserving
notification IDs and monitor assignments. Its Ansible task detects actual add or
update lines and suppresses credential-bearing command output. The API client
waits for its initial event lists before querying notifications and monitors.

Nextcloud password rotation remains pending: LXC 212 is deliberately stopped and
node1 lacks its `/mnt/nas/nextcloud` bind-mount source. Restore the NAS mount before
starting the guest, then rotate MariaDB credentials and update `config.php` and
both `.env` copies together. Merely changing `.env` does not rotate an initialized
database. No guest was started during preparation.
