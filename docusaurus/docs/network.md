# Network Design

This public snapshot uses example addresses in `10.0.0.0/22` and example service
domains. Adapt them to your own network before deployment.

All hosts sit in `10.0.0.0/22`; each tier occupies its own /24. LAN tier
segmentation is by IP range only: every LXC's interface is actually `/22`
(confirmed via `ip addr` on multiple hosts), not `/24`, and no firewall enforces the
boundary for LAN traffic. A host's tier is derivable from its IP, but any LAN
host can currently reach any other host across tier lines. Tailscale ACLs are
enforced via GitOps (`policy.hujson` and `.github/workflows/tailscale-acl.yml`;
see [ADR 0007](./decisions/0007-tailscale-acl-route-scoping.md)). The admin
ACL now expresses the same `/22` reach as four per-tier grants and tests it;
the union is unchanged. Proxmox firewall rules between LAN tiers are still
missing and the firewall remains disabled live. A manual, default-off host
ruleset is staged in `ansible/playbooks/pve-firewall.yml`; see
[ADR 0010](./decisions/0010-least-privilege-tailnet-and-host-firewall.md).

> The LXC and reverse-proxy tables below are **generated** from Terraform (`terraform/envs/*`) and the Caddyfile by `make docs`. Don't hand-edit anything between the `GENERATED` markers; change the source and regenerate. CI fails if they drift.

## IP Allocation

### 10.0.0.0/24: Infrastructure

| IP | Host | Role |
|----|------|------|
| .1 | router | Gateway |
| .3 | raspberrypi | Standalone AdGuard + Tailscale gateway; keeps DNS/VPN up when the cluster is powered off |
| .10 | node1 | Proxmox |
| .11 | node2 | Proxmox |
| .12 | node3 | Proxmox |
| .249 | nas | Synology DS923+ |

### 10.0.0.0/24: QEMU VMs (ad-hoc, not Terraform-managed)

Static IPs set inside each guest's own network config (not DHCP reservations); see AGENT.md's "Current QEMU VM inventory" for VMID/node placement.

| IP | Host | VMID |
|----|------|------|
| .44 | windowsvm00 | 400 |
| .45 | macosvm00 | 401 |
| .46 | archvm00 | 402 |
| .47 | ubuntuvm00 | 403 |

> **Moved from .68-.71 (2026-08-01).** The router hands out DHCP leases inside
> that range: a laptop was leased `10.0.0.68`, the same address
> windowsvm00 held statically. The laptop won the ARP race cluster-wide, so
> every host on the LAN resolved `.68` to the laptop and the VM was
> unreachable at its own documented address. Because these statics are set
> inside the guest, the DHCP server has no idea they exist and nothing
> prevents it from leasing them out.
>
> `.44-.47` is a quieter region, but **this is mitigation, not a fix**. The
> durable fix is to bound the router's DHCP pool (e.g. start it at `.100`) so
> it can never overlap the static block. Until that happens, any static in
> this /22 can collide with a new device joining the network.
>
> Diagnostic note: Windows Firewall blocks inbound ICMP by default, so
> windowsvm00 does **not** answer ping. A successful ping to its address means
> something *else* has taken it; test `nc -z <ip> 3389` instead.

### 10.0.1.0/24: Core LXCs (node1)

<!-- BEGIN GENERATED: lxc-core -->
| IP | Host | LXC | Role |
|----|------|-----|------|
| .10 | caddy | 111 | Reverse proxy |
| .11 | authentik | 112 | SSO |
| .12 | portainer | 113 | Docker UI |
| .13 | github-runner | 114 | CI/CD |
| .14 | semaphore | 115 | Ansible UI |
| .15 | tailscale | 116 | VPN + subnet router |
| .16 | adguard | 117 | DNS |
| .17 | docs | 118 | Docs site |
| .18 | prometheus | 119 | Metrics |
| .19 | grafana | 120 | Dashboards |
| .20 | uptime-kuma | 121 | Uptime monitoring |
| .21 | ntfy | 122 | Push notifications |
| .22 | jump | 123 | SSH bastion (LAN-only) |
| .23 | speedtest | 124 | Speedtest tracker |
<!-- END GENERATED: lxc-core -->

### 10.0.2.0/24: Prod LXCs

<!-- BEGIN GENERATED: lxc-prod -->
| IP | Host | LXC | Node | Role |
|----|------|-----|------|------|
| .10 | immich | 211 | node1 | Photos |
| .11 | nextcloud | 212 | node1 | Files |
| .12 | coolify | 213 | node3 | Deployment platform |
| .13 | searxng | 214 | node1 | Metasearch |
| .16 | airtrail | 217 | node3 |  |
| .17 | cobalt | 218 | node1 | Media downloader (cobalt.tools) |
| .18 | kavita | 219 | node1 |  |
| .19 | audiobookshelf | 220 | node1 |  |
| .20 | appdev00 | 221 | node1 | People Portal staging (Coolify remote) |
| .22 | homeassistant | 223 | node3 |  |
<!-- END GENERATED: lxc-prod -->

### 10.0.3.0/24: Test LXCs

<!-- BEGIN GENERATED: lxc-test -->
| IP | Host | LXC | Node | Role |
|----|------|-----|------|------|
| .10 | n8n | 601 | node1 | Automation |
| .11 | internship-watcher | 602 | node2 | Job scraper |
| .12 | kafka | 603 | node2 | Event streaming |
| .13 | openclaw | 604 | node2 | AI gateway (Claude) |
| .14 | dev | 605 | node1 | Personal dev box (Docker + Claude Code) |
<!-- END GENERATED: lxc-test -->

## DNS

Split DNS via AdGuard rewrites (`10.0.1.16`, backup on the Pi `.3`): `*.example.com` → Caddy, `*.example.internal` → the LXC's own IP. How a request flows (and Caddy's per-host DNS-01 certificates) is explained in [Architecture](./architecture.md#how-requests-flow-at-runtime); to add or change a record/route, use the [DNS and reverse-proxy runbook](./runbooks/dns-and-reverse-proxy.md).

## Reverse Proxy (Caddy, 10.0.1.10)

<!-- BEGIN GENERATED: reverse-proxy -->
| Subdomain | Backend |
|-----------|---------|
| pve1 | 10.0.0.10:8006 |
| pve2 | 10.0.0.11:8006 |
| pve3 | 10.0.0.12:8006 |
| auth | 10.0.1.11:9000 |
| portainer | 10.0.1.12:9443 |
| semaphore | 10.0.1.14:3000 |
| metrics | 10.0.1.18:9080 |
| grafana | 10.0.1.19:3000 |
| uptime | 10.0.1.20:3001 |
| ntfy | 10.0.1.21:80 |
| speedtest | 10.0.1.23:8765 |
| immich | 10.0.2.10:2283 |
| nextcloud | 10.0.2.11:8080 |
| coolify | 10.0.2.12:8000 |
| searxng | 10.0.2.13:8080 |
| airtrail | 10.0.2.16:3000 |
| cobalt | 10.0.2.17:8080 |
| api.cobalt | 10.0.2.17:9000 |
| kavita | 10.0.2.18:5000 |
| audiobookshelf | 10.0.2.19:13378 |
| homeassistant | 10.0.2.22:8123 |
| n8n | 10.0.3.10:5678 |
| internship-watcher | 10.0.3.11:8000 |
| kafka | 10.0.3.12:8080 |
| openclaw | 10.0.3.13:18789 |
<!-- END GENERATED: reverse-proxy -->

## WAN Inbound

80/443 TCP → 10.0.1.10 (Caddy); HTTP redirects to HTTPS.

> **Needs verification:** public hostnames are served through cloudflared
> tunnels, which need no inbound ports, so it is unconfirmed whether this
> router forward is still live. Check the router. If it is live, **every**
> Caddy site (including ones without Authentik in front) is reachable from
> the internet by SNI (`curl --resolve <host>:443:<WAN-IP> https://<host>`),
> regardless of whether a public DNS record exists for it.

## Remote Access: Tailscale (LXC 116)

The primary subnet router advertises `10.0.0.0/22` and the LAN IPv6
`/64`; exit node enabled; MagicDNS disabled (AdGuard handles DNS). ACL grants
scope the IPv4 destination by tier without changing the advertised `/22`.

**Exit-node DNS gotcha:** Tailscale makes the exit node the resolver for any
client using it, ignoring the tailnet's global nameservers. So the LXC's own
`resolv.conf` decides what exit-node clients get: left at the ISP default,
they bypass AdGuard (no filtering, no `*.example.internal` rewrites). The
compose `dns:` block pins the container's resolver to AdGuard
(`10.0.1.16`, then `10.0.0.3`) so exit-node clients keep AdGuard. The
admin console's per-nameserver "Use with exit node" toggle would also fix it,
but it isn't settable via the `tailscale` CLI or API and has been flaky.

## NAS

Synology DS923+, `10.0.0.249`. NFS export `/volume1/Ian` → `/mnt/nas`, bind-mounted into immich (`/mnt/nas/immich`) and nextcloud (`/mnt/nas/nextcloud`).
