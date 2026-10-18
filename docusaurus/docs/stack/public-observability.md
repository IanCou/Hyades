---
title: Public observability
sidebar_position: 46
---

# Public observability

The example domains in this public snapshot are deployment placeholders. Configure
your private origin outside the public repository before deployment.

A cached, read-only portfolio endpoint backed by private Prometheus metrics and
an explicit list of public HTTPS checks. The collector runs alongside Prometheus;
only its fixed JSON route is public. Neither a browser nor a public request can
choose a query, upstream URL, host, monitor, or label.

## Endpoint and sources

`GET https://metrics.example.com/v1/overview.json` (deployment placeholder)

`observability/Caddyfile.example` provides the exact public route with the reserved
origin `public-overview.internal.example:9080`. The active public-repository
Caddyfile and generated network table intentionally do not publish this route.
Supply the actual private origin in operator-managed configuration, then install
the route before configuring the external Tunnel hostname.

The source is `services/core/prometheus/observability/overview.py`; deployment
configuration is in `config.json` and the parent Compose stack. The background
collector refreshes on startup, then waits 60 seconds after each collection.
Requests only read the in-memory snapshot, so traffic does not multiply queries
against Prometheus. Restarting starts with unknown values until the first result.

| Field | Meaning |
| --- | --- |
| `cpuPercent` | Five-minute mean CPU busy percentage across the Proxmox host CPUs, weighted by CPU count. |
| `memoryPercent` | Capacity-weighted used memory, calculated from `MemAvailable` and `MemTotal` on the Proxmox hosts. |
| `storagePercent` | Capacity-weighted unavailable space on the hosts' **root filesystems only**, using filesystem available bytes. This is not local-lvm, ZFS pool, NAS, or guest-volume capacity. |
| `availabilityPercent` | Mean host-exporter scrape success over observed samples in the previous 24 hours. It is not application uptime; a fresh Prometheus installation has less than 24 hours of history. |
| `checks` | The configured public HTTPS entry points: 2xx/3xx is `operational`, other HTTP status codes are `degraded`. Transport/DNS/TLS errors cause stale/unknown results. Redirect destinations and authenticated application functionality are not checked. |

All resource queries select `job="proxmox"`. The playbook installs the native
Debian node-exporter package on those hosts, so the Docker/LXC exporters' `/rootfs`
mount configuration is not used. No container metrics are added to their host's
metrics. `expectedNodes` is three by default; missing targets/series fail the
resource aggregate instead of publishing a misleading percentage for a subset.
Resource collection also requires all expected host exporters to be up. Availability
can still report while a host is down, provided all expected scrape targets exist.

The committed check allowlist contains only the public portfolio and Hyades site.
It does not enumerate Kuma monitors. Uptime Kuma's internal API is not a dependency.
There is no backup, SMART, or scrub health claim because no trustworthy source is
configured for these checks. Add a real job/status source before displaying them.

## Response contract (version 1)

```json
{
  "schemaVersion": 1,
  "updatedAt": "2026-10-18T16:00:00Z",
  "stale": false,
  "fleet": {
    "cpuPercent": { "value": 32.4, "state": "fresh", "updatedAt": "2026-10-18T16:00:00Z" },
    "memoryPercent": { "value": 68.2, "state": "fresh", "updatedAt": "2026-10-18T16:00:00Z" },
    "storagePercent": { "value": 54.1, "state": "fresh", "updatedAt": "2026-10-18T16:00:00Z" },
    "availabilityPercent": { "value": 99.9, "state": "fresh", "updatedAt": "2026-10-18T16:00:00Z" }
  },
  "checks": [
    { "id": "personal-site", "name": "Personal site", "status": "operational", "state": "fresh", "updatedAt": "2026-10-18T16:00:00Z" }
  ]
}
```

The values above are illustrative. All percentages are finite numbers from 0 to
100, or `null` when unavailable. A check's status is `operational`, `degraded`, or
`unknown`. Each item has `state` (`fresh`, `stale`, or `unavailable`) and the timestamp
of its last successful observation. Top-level `updatedAt` is the last completed
collection attempt, **not** proof that every value is fresh. Top-level `stale` is
true if any item is stale or unavailable. No IPs, instance/host labels, URLs,
credentials, upstream response bodies, or exception details are returned.

- A failed refresh preserves that item's last successful value with `state: stale`.
- An item also becomes stale at 120 seconds old, even if the collector stalls.
- At 300 seconds old, a metric becomes `null` and a check becomes `unknown`, with
  `state: unavailable`. The old timestamp remains available for explanation.
- HTTP 200 means at least one item is still usable; it does not mean every service
  is healthy. Cold start or all values expired returns the same schema with HTTP 503.
- Completely fresh responses allow at most 30 seconds of caching with
  `must-revalidate`; the TTL is shortened near the 120-second stale boundary.
  Partial, stale, expired, and error responses use `Cache-Control: no-store`.
  There is no `stale-if-error` that could extend the five-minute lifetime.
- An ETag identifies a successful response. Conditional requests currently return
  the small full response rather than 304. Only GET, HEAD and exact-origin CORS
  preflight are supported. Query strings, other API paths, and write methods fail.

Render `null` as unavailable, and visibly mark stale values. Never label an old
`operational` check as currently healthy. Poll no faster than once per minute and
stop polling while the page is hidden. The portfolio is a separate consumer;
this PR does not replace its illustrative HTML values.

## Configuration and deployment

1. Review `observability/config.json`. `allowedOrigins` must contain exact browser
   origins, with no trailing slash or wildcard. HTTP is allowed only for explicit
   local-development origins; `file://`/`null` is not allowed. CORS is browser policy,
   not authentication: the sanitized JSON is intentionally public.
2. Review every `checks` name and URL for publication. Only public DNS names over
   HTTPS port 443 are allowed, with at most eight checks. Resolved addresses must
   all be globally routable; the TLS connection is pinned to a checked address
   while verifying the original hostname. Redirects are not followed. No
   credentials or tokens should be put in these URLs.
3. Install the example Caddy route using your private origin, review the plan,
   then deploy the two services from `ansible/`:

   ```bash
   ansible-playbook playbooks/prometheus.yml --check --diff
   ansible-playbook playbooks/caddy.yml --check --diff
   ansible-playbook playbooks/prometheus.yml
   ansible-playbook playbooks/caddy.yml
   ```

   The Prometheus playbook copies the collector/config directory and restarts the
   collector if either changes. The Compose container runs as UID 65534 with a
   read-only root filesystem, dropped capabilities, and resource limits. Port
   9080 is LAN-facing for Caddy; keep firewall access limited to the reverse proxy
   where host firewall rules are enabled. Prometheus's port 9090 stays private.
4. After replacing the reserved origin in operator-managed configuration, fetch `http://public-overview.internal.example:9080/v1/overview.json`.
   Confirm all three expected host exporters have a `/` filesystem series and
   compare the root-space definition with the hosts. Missing data must remain
   unavailable. `/healthz` only confirms the collector process is serving; it does
   not claim fresh upstream metrics and Caddy does not expose it publicly.
5. **External step:** create the `metrics.example.com` public hostname in Cloudflare
   Tunnel, pointing to the existing Caddy origin with that Host header. The route template does not create Tunnel hostname membership. Run the existing AdGuard
   rewrite playbook if LAN split DNS is desired. Review existing Caddy prerequisites
   before deployment, including the Authentik providers used by other routes.
6. Ensure Cloudflare/WAF/cache rules preserve `no-store` and `must-revalidate`;
   do not override the TTL or enable Always Online/stale serving for this path.
   An optional edge rate limit can further bound public traffic. Verify the public
   URL, CORS from the deployed portfolio, and cold/stale behavior before enabling
   the portfolio integration.

No secrets, Kuma login, Proxmox API token, or extra LXC is required. The collector
has private access to Prometheus over its Compose network. Do not route public
traffic to port 9090 or expose a parameterized Prometheus proxy. Public probes
run from Hyades' network and are one vantage point, not an independent external SLA.

## Review and rollback

Before deployment, review cold start, stale/expiry behavior, partial failures,
collector stalls, fixed routes, exact CORS, private DNS rejection, and redirect
handling. Live collection, firewall/edge behavior, and external tunnel configuration
need operator verification. No live deployment or upstream-metric comparison is
claimed by this change.

To roll back, remove the external Tunnel hostname first, revert this change, and
redeploy Caddy and Prometheus. Compose's existing `remove_orphans` behavior removes
the collector. Prometheus metrics data and scrape configuration are unchanged.

## References

- [Prometheus HTTP API](https://prometheus.io/docs/prometheus/latest/querying/api/)
- [Prometheus query functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Node exporter deployment modes](https://github.com/prometheus/node_exporter#installation-and-usage)
