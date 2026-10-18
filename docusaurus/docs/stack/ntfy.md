---
title: Ntfy
sidebar_position: 40
---

# Ntfy

Self-hosted push notification service, the alert sink for Uptime Kuma, Grafana, and
other lab jobs (e.g. [Internship Watcher](./internship-watcher.md), the jump-access audit).

Config: [services/core/ntfy/](https://github.com/IanCou/Hyades/tree/main/services/core/ntfy) · IP/LXC/route: [network.md](../network.md)

## Auth

Access is **deny-all by default** (`auth-default-access: deny-all`). Admin user created
at first deploy:

```bash
docker exec -i ntfy-ntfy-1 ntfy user add --role=admin <username>
# prompts for password
```

To add a publish-only service account:

```bash
docker exec -i ntfy-ntfy-1 ntfy user add alerts-publisher
docker exec ntfy-ntfy-1 ntfy access alerts-publisher homelab write-only
```

## Topics

| Topic     | Purpose                                           |
| --------- | ------------------------------------------------- |
| `homelab` | All infrastructure alerts (Uptime Kuma + Grafana) |

## Wiring

- **Uptime Kuma**: provisioned as code by `setup_monitors.py`; see
  [Uptime Kuma](./uptime-kuma.md#alerting).
- **Grafana**: **Alerting → Contact points → Add**, type **ntfy** (or Webhook with URL
  `https://<user>:<password>@ntfy.example.com/homelab`, method POST, message
  `{{ $values }}`), then attach to a **Notification policy** covering all alert rules.

## Prometheus metrics

Metrics on `:9998/metrics` are **unauthenticated**; already a scrape target (job `ntfy`) in
`services/core/prometheus/prometheus.yml.j2`.

## References

- [ntfy docs](https://docs.ntfy.sh)
- [ntfy GitHub](https://github.com/binwiederhier/ntfy)
