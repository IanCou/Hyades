# 0003. Static tier-per-node placement

**Status:** Accepted (revisit; see risks)

## Context

Workloads are grouped into tiers (**core**, **prod**, **test**), and each tier
maps to a fixed node and its own /24 subnet:

| Tier | Node          | Subnet        | Terraform env         |
| ---- | ------------- | ------------- | --------------------- |
| core | node1         | `10.0.1.0/24` | `terraform/envs/core` |
| prod | node1 + node3 | `10.0.2.0/24` | `terraform/envs/prod` |
| test | node2         | `10.0.3.0/24` | `terraform/envs/test` |

This makes "where does service X live and what is its IP" answerable from the tier
alone, and keeps each Terraform env pointed at one node. The cost is that
placement is by _tier label_, not by _node capacity_. Today node1 carries the core
tier plus most of prod, roughly **17 LXCs** (and NAS bind mounts for Immich and
Nextcloud), while **node3 runs 2** and node2 runs only the test tier. The mapping
is convenient but lopsided.

## Options considered

### Option A: Static tier-per-node mapping (chosen)

- **Pros:** Dead simple mental model: tier ⇒ node ⇒ subnet. Each Terraform env
  targets one node, so blast radius of a `terraform apply` is one tier. IP and
  location are derivable from the tier with no scheduler to consult.
- **Cons:** Placement ignores load. node1 is a **single point of failure** running
  ~17 LXCs (core DNS, proxy, runner, SSO, monitoring) plus NAS-backed prod apps,
  while node3 sits near-idle at 2 LXCs. Losing node1 takes down the bulk of the
  homelab; the other 16 GB of cluster RAM is largely stranded.

### Option B: Manual capacity-balanced placement

- **Pros:** Spreads load to use node2/node3 RAM; can pull critical services off
  node1 to shrink the SPOF.
- **Cons:** Breaks the clean tier⇒node⇒subnet rule; placement decisions become
  ad-hoc and must be tracked by hand. Still no automatic recovery on node failure.

### Option C: Anti-affinity / HA scheduling (Proxmox HA groups or similar)

- **Pros:** Critical services restart elsewhere automatically; anti-affinity rules
  keep redundant services off the same node. Capacity-aware placement.
- **Cons:** Real complexity for a 3-node single-operator cluster: shared/replicated
  storage for stateful LXCs, HA fencing, and per-service affinity rules. Most
  services here are stateful with local or single-node NAS mounts, so naive HA
  failover risks data, not just downtime.

## Decision

Keep the static tier-per-node mapping for now. Its simplicity is worth more than
balance while the cluster is small and operated by one person, and the imbalance is
understood rather than accidental.

## Consequences

### Positive

- Location and IP of any service follow from its tier with no lookup.
- Each `terraform apply` is scoped to one node/tier, limiting accidental change.
- New services have an obvious, rule-based home.

### Negative / risks

- **node1 is a SPOF** hosting ~17 LXCs including core DNS, the reverse proxy, and
  monitoring; its loss is a near-total outage. The Pi secondary in ADR
  [0004](./0004-split-dns-with-pi-secondary.md) deliberately keeps DNS/VPN alive
  through exactly this case, but application services stay down.
- Cluster capacity is poorly used: node3 runs 2 LXCs while node1 is saturated.
- **Future direction:** move toward capacity-aware placement with anti-affinity for
  redundant services, starting by relocating stateless core services off node1.
  Revisit this ADR (and supersede it) once that work lands; the blockers are
  shared storage for stateful LXCs and reworking the per-node Terraform envs.

## Update (2026-10-17)

node1 and node2 have been upgraded from 8 GB to 24 GB of RAM; node3 is still
8 GB (~56 GB cluster total), so the "other 16 GB" figure above reflects the
hardware at decision time. node2 now has ~18 GB free and is the rebalancing
target; node3 has no headroom. Rebalancing stateless services off node1 onto
node2 (Option B, or the first step of the future direction above) is now
feasible on capacity grounds; the remaining blockers are the operational ones
listed above, not RAM.
