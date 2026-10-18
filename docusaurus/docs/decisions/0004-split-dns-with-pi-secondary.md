# 0004. Split-horizon DNS with an off-cluster Pi secondary

**Status:** Accepted

## Context

Internal name resolution uses split-horizon DNS on AdGuard Home (LXC 117,
`10.0.1.16`):

- `*.example.com` → Caddy (web UIs, behind TLS)
- `*.example.internal` → direct LXC IP (SSH and non-proxied access)

Both wildcards are AdGuard rewrites. AdGuard is also the LAN's recursive resolver
and ad/tracker filter, so **DNS is on the critical path for the entire network**:
if it's down, internal name resolution and general browsing degrade for every
device, not just homelab services.

That creates a circular dependency: the primary AdGuard runs as an LXC _on the
cluster_. Per ADR [0003](./0003-tier-per-node-placement.md), node1 is a SPOF, and a
full cluster power-off (maintenance, power outage, breaker) would take DNS down
with it, and with it remote access, since the Tailscale subnet router (LXC 116)
is also on the cluster.

## Options considered

### Option A: Single AdGuard LXC on the cluster

- **Pros:** Simplest; one instance to configure. Lives in the same IaC pipeline as
  everything else.
- **Cons:** DNS dies whenever node1 or the whole cluster is down, i.e. exactly
  when you most need to reach the cluster to fix it. VPN also depends on the
  cluster, so recovery is hard from off-LAN.

### Option B: Two AdGuard LXCs on different cluster nodes

- **Pros:** Survives a single-node failure; both managed as code.
- **Cons:** A full cluster power-off still kills both. Doesn't break the "DNS
  depends on the thing DNS is needed to fix" cycle.

### Option C: Cluster AdGuard + an off-cluster Raspberry Pi secondary (chosen)

- **Pros:** A standalone Pi at `10.0.0.3` runs a **second AdGuard plus
  Tailscale**, drawing only a few watts and independent of Proxmox. DNS _and_ VPN
  survive a complete cluster power-off, so the LAN keeps resolving names and the
  cluster stays remotely reachable to bring it back. Handed out as a secondary
  resolver via DHCP, it also covers cluster-side AdGuard restarts.
- **Cons:** A second device to keep patched and in sync; it sits **outside** the
  Terraform/Ansible pipeline (standalone, hand-managed). Rewrite rules can drift
  between the two AdGuards if updated in only one place.

## Decision

Run split-horizon DNS on the cluster AdGuard as primary, and a second independent
AdGuard + Tailscale on an off-cluster Raspberry Pi (`10.0.0.3`) as the
resilience anchor for DNS and VPN.

The deciding factor is breaking the circular dependency: keeping resolution and
remote access alive when the cluster is entirely off is worth one extra
hand-managed device.

## Consequences

### Positive

- DNS and VPN survive a full cluster outage; the LAN keeps working and the cluster
  stays remotely reachable for recovery.
- The Pi's tiny power draw makes always-on cheap, with no Proxmox dependency.

### Negative / risks

- The Pi is **outside the IaC pipeline**: manual patching and config, the main
  off-code exception in the homelab.
- Rewrite rules can drift between the two AdGuards; they must be updated in both.
- Revisit if the Pi's manual management becomes a burden; candidate fixes are
  config sync automation or folding it into Ansible while keeping it off-cluster.
