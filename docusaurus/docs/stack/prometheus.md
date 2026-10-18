---
title: Prometheus
sidebar_position: 45
---

# Prometheus

Time-series metrics database. Scrapes `node_exporter` on every LXC plus the Proxmox nodes;
paired with [Grafana](./grafana.md) for dashboarding.

Config: [services/core/prometheus/](https://github.com/IanCou/Hyades/tree/main/services/core/prometheus) · IP/LXC/route: [network.md](../network.md)

## Access posture

The Prometheus UI/API has no public DNS or Caddy route; reach the UI directly at `http://10.0.1.18:9090` from
the LAN/Tailscale.

The separate [public observability collector](./public-observability.md) runs in
this Compose stack on port `9080`. Caddy forwards only its fixed summary route;
Prometheus's `9090` remains private.

## Deploy

**Not** deployed by the standard `deploy.yml`; use `ansible-playbook playbooks/prometheus.yml`,
which additionally:

- Renders `services/core/prometheus/prometheus.yml.j2` against the Ansible inventory to
  `/opt/services/prometheus/prometheus.yml`, after `promtool check config` passes on the
  render; edit the template or inventory and redeploy, never the file on the host.
- Sends Prometheus `SIGHUP` when the rendered file changes (a bind-mounted file change
  doesn't recreate the container), then fails the run unless Prometheus's own
  `prometheus_config_last_reload_*` metrics show the new config loaded. No
  `--web.enable-lifecycle`: that would expose an unauthenticated `/-/reload` and
  `/-/quit` on `:9090`.
- Creates `/data/prometheus` owned by UID `65534` (`nobody`), which the container runs as.
  Without this the TSDB cannot write and the container crash-loops.

## Adding scrape targets

Targets come from `ansible/inventory/hosts.yml`; there is no list to edit. One job per
group, job names unchanged from the old static file so dashboards keep working:

| Job        | Inventory groups    |
| ---------- | ------------------- |
| `proxmox`  | `proxmox_nodes`     |
| `core`     | `core`, `runners`   |
| `prod`     | `prod`              |
| `test`     | `test`              |
| `gateways` | `gateways` (the Pi) |
| `ntfy`     | ntfy's `:9998`      |

Each target is `ansible_host:9100` with a `host` label holding the inventory name
(`instance` stays the default IP:port). Not scraped: the `stopped` group, filled at deploy time from
live Proxmox power state (so `up == 0` means broken, not parked) and `bastions`/`legacy_vms`/`desktop_vms` (no `node_exporter`
on them). `node_exporter` must be listening on `:9100` on each scraped host. CI redeploys
Prometheus on any inventory change.

Where each host's `node_exporter` comes from (all via `ansible-playbook playbooks/node-exporter.yml`):

| Hosts               | Install                                                               |
| ------------------- | --------------------------------------------------------------------- |
| `docker_hosts` LXCs | shared docker stack, `services/_shared/node-exporter/`                |
| the Pi (ARMv6)      | Debian `prometheus-node-exporter` (no armv6 image)                    |
| `proxmox_nodes`     | Debian `prometheus-node-exporter`, no Recommends (`-l proxmox_nodes`) |

The PVE firewall is disabled cluster-wide, so nothing gates `:9100` on the nodes. If it is
ever enabled, allow `9100/tcp` from `10.0.1.18`.

## References

- [Prometheus docs](https://prometheus.io/docs/)
- [node_exporter](https://github.com/prometheus/node_exporter)
