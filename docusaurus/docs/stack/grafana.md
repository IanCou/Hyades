---
title: Grafana + Prometheus
sidebar_position: 35
---

# Grafana + Prometheus

Metrics collection and dashboarding: [Prometheus](./prometheus.md) scrapes the Proxmox
nodes and LXCs; Grafana visualizes them. Grafana sits behind Caddy's Authentik
forward-auth gate (see [Authentik](./authentik.md)).

Prometheus deploys with its own `ansible-playbook playbooks/prometheus.yml` (see
[Prometheus](./prometheus.md) for why); Grafana uses the standard `deploy.yml`.

Config: [services/core/grafana/](https://github.com/IanCou/Hyades/tree/main/services/core/grafana) · IP/LXC/route: [network.md](../network.md)

## Grafana datasource

After deploy, add Prometheus as a data source in Grafana UI:
**Connections → Data sources → Add → Prometheus → URL: `http://10.0.1.18:9090`**

## Dashboards

Recommended Grafana dashboard IDs to import:

| Dashboard              | ID      |
| ---------------------- | ------- |
| Node Exporter Full     | `1860`  |
| Proxmox via Prometheus | `10347` |

## Proxmox integration

Proxmox metrics per VM/CT (CPU, memory, disk per container) come via
[`prometheus-pve-exporter`](https://github.com/prometheus-pve/prometheus-pve-exporter)
(`pip install prometheus-pve-exporter`), added as a scrape target alongside
`node_exporter`.

## References

- [Prometheus docs](https://prometheus.io/docs/)
- [Grafana docs](https://grafana.com/docs/)
