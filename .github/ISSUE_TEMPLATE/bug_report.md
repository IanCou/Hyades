---
name: Bug / something broken
about: A service, deploy, or piece of infra isn't behaving
title: "[bug] "
labels: bug
---

## What's broken

<!-- What's not working, and where? -->

## Affected service / tier / host

<!-- e.g. prod/immich on lxc-110, or core/caddy, or the docs site -->

## Expected vs. actual

- **Expected:**
- **Actual:**

## Steps to reproduce

1.

## Logs / output

<!--
Paste relevant output. Scrub secrets first.
Useful sources: `docker compose logs`, `journalctl -u <unit>`, the GitHub Actions
run, or `make plan service=<name>` run locally.
-->

```text

```

## Environment

- Reached via: <!-- LAN / Tailscale / public hostname -->
- Recent changes: <!-- last deploy, PR, or config edit that might be related -->
