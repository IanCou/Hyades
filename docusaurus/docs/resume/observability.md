---
title: Observability
sidebar_position: 5
---

# Observability

A monitoring pipeline with four layers, answering two different questions: "is each host healthy?" (metrics) and "is each service actually reachable?" (liveness).

## Metrics: node_exporter → Prometheus → Grafana

`node_exporter` runs on every host as one shared stack (`services/_shared/node-exporter/`, deployed via a dedicated playbook), rather than duplicated inside every service's own compose file; centralizing it ensures new services do not omit host metrics. [Prometheus](../stack/prometheus.md) scrapes every target on a 15s interval, with separate jobs per tier plus a job for the three Proxmox nodes. Its data directory has to be owned by UID `65534` or the container crash-loops, a gotcha captured in AGENT.md and handled automatically by its deploy playbook.

[Grafana](../stack/grafana.md) sits on top as the visualization layer, using community dashboards for per-host and per-VM metrics.

## Liveness: Uptime Kuma

[Uptime Kuma](../stack/uptime-kuma.md) does black-box HTTP/ping checks against the actual endpoints, provisioned as code via an idempotent script rather than hand-clicked, so the monitor set is reproducible. Non-tunnel monitors target the direct LXC IP:port rather than the public hostname, since the Uptime Kuma LXC resolves public DNS and internal-only `*.example.com` names don't resolve to Caddy from inside.

## Alerting: ntfy

[ntfy](../stack/ntfy.md) is the self-hosted push-notification sink: both Uptime Kuma and Grafana publish to it, so a down endpoint or a fired rule lands as a phone push. It also exposes its own Prometheus metrics, so the alerter itself is monitored.

## Why both metrics and liveness

White-box metrics (Prometheus and Grafana) track system resource utilization across hosts and containers. Black-box checks (Uptime Kuma) independently test endpoint reachability and HTTP response codes. Combining both separates host health from service availability: an LXC can maintain normal CPU and memory utilization while its application process is unresponsive, or an application can remain healthy while upstream routing fails. In addition, Prometheus pull-based scraping surfaces unreachable targets directly when a scrape fails.
