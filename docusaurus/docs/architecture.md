---
sidebar_position: 1
---

# Architecture

How this repo is laid out, how a change gets from a `git push` to a running
container, and how a client request reaches a service at runtime.

For the authoritative IP/DNS/topology tables see [`network.md`](./network.md).
For day-to-day workflow and gotchas see [`AGENT.md`](https://github.com/IanCou/Hyades/blob/main/AGENT.md)
at the repo root.

## Repo structure

The repo is a single source of truth for a 3-node Proxmox cluster. Each layer
owns one concern: Terraform provisions, Ansible configures, Compose runs the
workloads, Caddy/AdGuard handle ingress.

```text
.
├── terraform/                 Provisioning: defines the LXC containers
│   ├── modules/lxc-docker/    Reusable LXC module (CPU/RAM/disk/IP/tags)
│   └── envs/{core,prod,test}/ One env per tier; main.tf = the LXC inventory
├── ansible/                   Configuration management
│   ├── inventory/hosts.yml    All hosts + their service/tier vars (IPs, roles)
│   ├── playbooks/             One playbook per operation (deploy, caddy, docs…)
│   ├── roles/                 docker, cloudflared, github-runner, portainer-agent
│   └── group_vars/            Shared/vaulted variables
├── services/                  Docker Compose stacks, grouped by tier
│   ├── core/<svc>/            node1 infra (caddy, adguard, prometheus, grafana…)
│   ├── prod/<svc>/            node1+node3 user-facing apps (immich, nextcloud…)
│   ├── test/<svc>/            node1+node2 experiments (n8n, kafka, internship-watcher…)
│   └── gateways/adguard/      Standalone Raspberry Pi AdGuard stack
├── docusaurus/                Documentation site (Docusaurus 3.10 / MDX v3)
│   └── docs/                  Source markdown; sidebar auto-generated from tree
├── scripts/gen_docs.py        Regenerates the GENERATED tables in network.md
├── .github/workflows/ci.yml    CI: validate, lint, secret-scan → deploy on the runner
├── Makefile                   `make docs` / `make docs-check` wrappers for gen_docs.py
└── AGENT.md                   Authoritative contributor guide (read first)
```

## How a change ships

Recurring service and docs changes deploy through CI on a self-hosted GitHub
runner (LXC 114). There is no manual `docker compose up` on the target in the
normal path; pushing to `main` is the deploy.

```text
git push (main)
      ▼
.github/workflows/ci.yml
      │
      ├─ validate (ubuntu-latest)
      │     • gen_docs.py --check   (network.md tables in sync)
      │     • YAML parse             (changed compose stacks)
      │     • caddy adapt            (if Caddyfile changed; pure syntax check)
      │     • ansible --syntax-check  (+ ansible-lint)
      │     • terraform fmt + validate (if terraform changed)
      ├─ lint (ubuntu-latest: Prettier, markdownlint, actionlint)
      ├─ secret-scan (ubuntu-latest: gitleaks)
      │
      ▼
      └─ deploy (self-hosted; needs all three checks; push to main only)
            • runs when services or docusaurus/ changed
            • for each changed service:
                playbooks/<service>.yml   if one exists (caddy, internship-watcher…)
                else playbooks/deploy.yml -l <service>
            • playbooks/docs.yml          if docusaurus/ changed
                  │
                  ▼
            ansible copies services/<tier>/<svc>/docker-compose.yml (+ .env)
            → /opt/services/<svc>/ on the target LXC
            → docker compose up (pull: always)
```

Key files:

- Pipeline:
  [`.github/workflows/ci.yml`](https://github.com/IanCou/Hyades/blob/main/.github/workflows/ci.yml).
  The `validate`, `lint`, and `secret-scan` jobs gate the `deploy` job.
- Generic deploy: `ansible/playbooks/deploy.yml` copies the compose file
  (and `.env` if present) to `/opt/services/<svc>/` and runs `docker compose up`.
- Service-specific playbooks (e.g. `caddy.yml`, `internship-watcher.yml`) handle
  locally-built images or extra files; CI prefers them when present.
- Doc tables: `scripts/gen_docs.py` derives the LXC and reverse-proxy tables in
  `network.md` from Terraform + the Caddyfile. Run `make docs` after changing
  the inventory or CI's `gen_docs.py --check` will fail.

Provisioning a brand-new LXC (Terraform `apply`) and the first Docker install
(`ansible/playbooks/docker.yml`) are still run manually (see the
"Add a new service" checklist in `AGENT.md`). CI handles the recurring
config/compose deploys only.

## How requests flow at runtime

DNS resolution decides the path. Both wildcards live in AdGuard
(`10.0.1.16`); everything else forwards upstream.

```text
                         ┌──────────────────────────────────────┐
client (LAN / Tailscale) │ DNS query → AdGuard (10.0.1.16)  │
                         └──────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       │ *.example.com          │ *.example.internal     │
       ▼                            │                             ▼
  Caddy (10.0.1.10)            │                    direct LXC IP
  TLS: per-host certificates       │                    (SSH / raw port)
  (Cloudflare DNS-01)              │
       │                           │
       ▼                           ▼
  reverse_proxy → service LXC  (e.g. immich 10.0.2.10:2283)
```

- `*.example.com` → Caddy at `10.0.1.10`, which terminates TLS (one
  DNS-01 certificate per configured host via Cloudflare) and reverse-proxies to
  the service's `LXC-IP:port`. Routes are defined in `services/core/caddy/Caddyfile` and
  mirrored in the generated reverse-proxy table in [`network.md`](./network.md).
- `*.example.internal` → the LXC IP directly (SSH and raw-port access),
  bypassing Caddy.
- The Raspberry Pi gateway (`10.0.0.3`) runs a second standalone AdGuard so
  DNS keeps working when the cluster is powered off. Tailscale is installed
  natively via apt on the Pi; the primary Tailscale stack is
  `services/core/tailscale/` on LXC 116.

Remote access (off-LAN):

- **Tailscale** (LXC 116) advertises subnet `10.0.0.0/22` and acts as an
  exit node, so a remote tailnet client reaches every LXC by its LAN IP and
  resolves names through the same AdGuard split-DNS.
- **Cloudflared** tunnels expose selected public hostnames inbound without
  opening WAN ports. A WAN `80/443` → Caddy forward is also documented, but
  whether it is still live is unverified (see
  [WAN Inbound](./network.md#wan-inbound)).

## End-to-end stack

How the layers fit together: provisioning to observability.

```text
  PROVISION            CONFIGURE              WORKLOADS
  ─────────            ─────────              ─────────
  Terraform   ──────▶  Ansible      ──────▶   Docker Compose
  lxc-docker           roles:                 services/<tier>/<svc>/
  module               docker,                docker-compose.yml
  envs/{core,           cloudflared,          (+ node_exporter, deployed
   prod,test}           github-runner,         once per host as its own
                        portainer-agent        shared stack)
        │                                          │
        │                                          ▼
        │                                   INGRESS
        │                                   ───────
        │                                   AdGuard split DNS
        │                                   → Caddy reverse proxy
        │                                   → Cloudflared / Tailscale
        ▼                                          │
  network.md tables  ◀── gen_docs.py              ▼
  (Terraform + Caddyfile)                   OBSERVABILITY
                                            ─────────────
                                            Prometheus  scrapes :9100 (all LXCs)
                                            Grafana     dashboards
                                            Uptime-Kuma HTTP/ping monitors
                                            ntfy        push alerts
```

`node_exporter` is deployed once per host as a shared stack
(`services/_shared/node-exporter/`, `network_mode: host`, `pid: host`) on
`:9100`, rather than duplicated inside every service's own compose file.
Prometheus (`10.0.1.18`) scrapes all of them every 15s and Grafana
(`10.0.1.19`) renders them. Uptime-Kuma watches service endpoints and
ntfy delivers push alerts.

## See also

- [`network.md`](./network.md): authoritative IPs, subnets, DNS, proxy routes.
- [`proxmox.md`](./proxmox.md): cluster and node detail.
- [`AGENT.md`](https://github.com/IanCou/Hyades/blob/main/AGENT.md):
  contributor workflow, special playbooks, gotchas.
