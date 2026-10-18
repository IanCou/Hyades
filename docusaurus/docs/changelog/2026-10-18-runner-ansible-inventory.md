---
title: "2026-10-18: CI runner missing ansible-inventory"
sidebar_position: 2
---

# 2026-10-18: CI runner missing `ansible-inventory`

## What broke

The deploy job's new "Read guest power state from Proxmox" step (`86194f7`)
runs `scripts/proxmox_power_state.py`, which calls `ansible-inventory --list`.
On the self-hosted runner (LXC 114) it died with
`FileNotFoundError: [Errno 2] No such file or directory: 'ansible-inventory'`
before touching any host. Two runs failed this way:

- `39160219243` (`86194f7`): its deploy was applied by hand instead.
- `39164758022` (`04bc78d`): the node_exporter-on-Proxmox change and its docs
  page did not deploy.

## Why only `ansible-inventory`

Ansible lives in a venv at `/opt/ansible-venv`. `roles/github-runner` symlinked
a hand-kept list of 4 entry points into `/usr/local/bin`: `ansible`,
`ansible-playbook`, `ansible-galaxy` and `ansible-vault`. The venv ships 11.
Every earlier CI step only used the linked ones, so the gap stayed hidden until
the first call to an unlisted binary.

## Fix

Two PRs, same day:

- #65 (`71c014b`): `scripts/proxmox_power_state.py` resolves
  `ansible-inventory` from `PATH`, then falls back to the venv that
  `ansible-playbook` symlinks into, and exits with a `::error::` if neither has
  it. The role's fixed list gained `ansible-inventory`.
- This PR: `ansible/roles/github-runner/tasks/main.yml` drops the fixed list.
  It `find`s every `ansible*` file in `/opt/ansible-venv/bin` and links each
  one, so a future CI step that calls `ansible-config` or `ansible-doc` already
  resolves.

Applied to the runner with
`ansible-playbook playbooks/setup-runner.yml -l github-runner`. `--check --diff`
first showed exactly 7 new links (`ansible-inventory`, `-config`, `-console`,
`-doc`, `-pull`, `-test`, `-community`) and no other change. The runner was
already registered, so the registration tasks skipped. The second play
(pubkey to `docker_hosts`) matched nothing under the limit.

## Verification

- On the runner: `command -v ansible-inventory` → `/usr/local/bin/ansible-inventory`,
  `ansible-inventory --version` → core 2.19.8.
- Re-ran the failed deploy job of `39164758022` (no code change needed, the
  fix is on the runner). The power-state step printed
  `stopped (from Proxmox): archvm00, core-services, immich, internship-watcher, nextcloud, prod-services, test-services, ubuntuvm00`
  and the job passed. `04bc78d` changed no `services/` path, so "Deploy changed
  services" skipped; the playbook change itself was applied by hand in #66.
  "Deploy docs site" ran (`docs: ok=5 changed=2`) and
  `/docs/changelog/2026-10-18-proxmox-node-exporter/` now returns 200.

## Files touched

- `ansible/roles/github-runner/tasks/main.yml` (this PR)
- `scripts/proxmox_power_state.py` (#65)
