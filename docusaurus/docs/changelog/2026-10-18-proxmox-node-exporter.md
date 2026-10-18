---
title: "2026-10-18: node_exporter on the Proxmox nodes"
sidebar_position: 3
---

# 2026-10-18: node_exporter on the Proxmox nodes

## What was wrong

After the inventory-rendered Prometheus targets shipped (same day, `86194f7`),
28 of 31 targets were up. The 3 down were the `proxmox` job: node1, node2 and
node3 (`10.0.0.10`-`.12:9100`), all `connection refused`. Nothing ever
installed `node_exporter` on the hypervisors. `node-exporter.yml` only targeted
`docker_hosts`, and the PVE hosts run no docker. The job had been scraping
empty ports since the static config was first written. This was not a
regression from `86194f7`.

## Fix

`ansible/playbooks/node-exporter.yml` has a second play for `proxmox_nodes`.
It installs Debian's `prometheus-node-exporter` (1.9.0) and enables the unit,
the same path the Pi already uses.

- `install_recommends: false`. With Recommends, apt also pulled in
  `prometheus-node-exporter-collectors`, `ipmitool`, `openipmi` and `nvme-cli`,
  and upgraded 14 base packages (`util-linux`, `mount`, `login`, ...) on the
  hypervisors as a side effect. Without them it is 1 new package and 0
  upgrades. Upgrading the nodes stays a deliberate `apt full-upgrade`.
- The enable/start task sets `ignore_errors: "{{ ansible_check_mode }}"`.
  In `--check` the package is never really installed, so on a first run the
  unit doesn't exist and the task would fail.
- Host patterns: the docker play is now
  `"{{ target | default('docker_hosts') }}:!proxmox_nodes"` and the new play is
  `"{{ target | default('proxmox_nodes') }}:&proxmox_nodes"`. The default run
  still picks the same 30 docker hosts. `-e target=node1` now reaches only the
  apt play, never the docker path. `-l <service>` matches nothing in the
  Proxmox play and skips it.

## Firewall

`pve-firewall status` reports `disabled/running` on all three nodes, and
`/etc/pve/firewall/` holds no `cluster.fw`. Nothing filters `:9100`, so no rule
was added. If the PVE firewall is ever enabled, allow `9100/tcp` from
Prometheus (`10.0.1.18`).

## Verification

- `ansible-playbook playbooks/node-exporter.yml -l proxmox_nodes --check --diff`:
  1 package to install per node, 0 upgrades.
- Real run: `changed=1` per node. Re-run: `changed=0`.
- `curl http://10.0.0.1{0,1,2}:9100/metrics`: `node_exporter_build_info`
  version `1.9.0` on all three.
- `http://10.0.1.18:9090/api/v1/targets`: all 3 `proxmox` targets
  `health: up`, 31/31 targets up overall.

## CI note

CI runs `node-exporter.yml` with `-l 'all:!ci_deploy_skip'` whenever
`services/_shared/node-exporter/` changes, so that deploy now also runs the
apt play on the nodes. The runner already SSHes to them as root for
`proxmox_power_state.py`, and the play is idempotent. A change to the playbook
alone does not trigger a deploy.

## Files touched

- `ansible/playbooks/node-exporter.yml`: Proxmox play, `:!proxmox_nodes` on the docker play
- `docusaurus/docs/stack/prometheus.md`: where each host group's exporter comes from, firewall note
- `AGENT.md`: playbook table row, monitoring line
