# 0010. Least-privilege tailnet access and staged Proxmox host firewall

**Status:** Accepted

## Context

The Tailscale policy granted `tag:homelab-admin` every protocol and port in
`10.0.0.0/22` and the LAN IPv6 `/64`. That access was intentional, but one
aggregate destination hid the infra, core, prod, and test trust boundaries and
had no policy self-tests. Any edit to that rule could remove the operator's only
remote recovery path when the GitOps workflow applies the policy on merge.

The primary subnet router is LXC 116 at `10.0.1.15`. Its Compose file uses
host networking and advertises `10.0.0.0/22`,
`fd00:db8::/64`, and an exit node. The Pi fallback at
`10.0.0.3` advertises the IPv4 `/22` and an exit node in the checked-in
setup command, but does not currently advertise the IPv6 `/64`. Neither file
sets `--snat-subnet-routes=false`, so Tailscale's default subnet-route SNAT
applies. This is verified from
`services/core/tailscale/docker-compose.yml` and
`services/core/tailscale/raspberrypi-setup.md`, not observed live. A LAN host
therefore sees subnet-routed tailnet traffic as coming from `10.0.1.15` or
`10.0.0.3`, not from the original tailnet identity. Per-identity controls
must remain in the Tailscale ACL; a Proxmox host firewall can only allowlist
the routers' translated LAN addresses.

The Proxmox firewall remains disabled live. Proxmox nodes expose SSH, the
`:8006` UI, and node exporter on the flat LAN. Enabling a mistaken host policy
can remove SSH and UI recovery on all three nodes at once because
`/etc/pve/firewall/cluster.fw` lives in the cluster-wide pmxcfs filesystem.
The inventory contains no operator workstation IP or DHCP reservation to
allowlist.

## Options considered

### Option A: Keep aggregate ACL grants and leave the host firewall unmanaged

- **Pros:** No rollout work and no new lockout path.
- **Cons:** A future ACL edit still changes all four tiers at once, access
  intent has no executable regression tests, and there is no reviewable host
  firewall configuration or rollback procedure.

### Option B: Split ACL grants by tier and stage a default-off host firewall (chosen)

- **Pros:** The admin grant retains the exact IPv4 `/22` and IPv6 `/64` reach
  it has today, but each tier can be reviewed and narrowed independently.
  Positive and negative tests pin admin, viewer, and gateway behavior. The
  host firewall is reviewable, requires an explicit confirmation variable,
  and remains disabled until a console-backed manual rollout.
- **Cons:** The policy and firewall templates have more entries to keep in
  sync. An incorrect destination, source IP, or `management` IPSet can lock
  out the operator, CI runner, or monitoring. SNAT prevents the host firewall
  from distinguishing individual tailnet users.

### Option C: Enable a restrictive Proxmox firewall through Terraform

- **Pros:** One provisioning tool could own nodes and their firewall state.
- **Cons:** pmxcfs replicates cluster firewall state, so a resource associated
  with one Terraform environment can affect all nodes. Existing CI applies
  Terraform changes automatically after merge. That is too direct a path from
  a routine apply to cluster-wide management lockout.

## Decision

Choose Option B.

`policy.hujson` now defines aliases for every tier and critical endpoint. Four
separate wildcard grants give `tag:homelab-admin` the exact union of
`10.0.0.0/24` through `10.0.3.0/24`; a fifth retains the existing
IPv6 `/64`. The exit-node grant still names `tag:homelab-admin` explicitly,
as required by ADR 0007. Removing it would strand a tagged admin because
tagged devices are not members of `autogroup:member`.

`tag:homelab-viewer` is opt-in and currently assigned to no device. It permits
TCP 80 and 443 to prod and Caddy, plus TCP and UDP 53 to AdGuard. It is also
listed on the exit-node grant for the same tagged-device reason. Tests prove
that admin keeps representative access across every tier, viewer cannot reach
SSH, Proxmox, Prometheus, or test directly, and a gateway tag has no LAN
grants of its own. The boundary is network-level only: Caddy on 443 proxies
every route it serves, including `pve1`-`pve3`, so a viewer can still load
those apps through Caddy and is stopped only by each app's own login or
Authentik. Drop `caddy` from the viewer grant if that matters. `python3 scripts/check_policy.py` is the local pre-PR check for alias,
tag, test, admin coverage, and exit-node invariants. The GitOps workflow remains
the authoritative Tailscale policy validator.

The host policy is a manual Ansible playbook, not a Terraform resource. It
targets `proxmox_nodes`, writes one shared `cluster.fw` from one node, backs up
the prior file, and runs `pve-firewall compile` without starting or restarting
the firewall. Defaults are `enable: 0`, `policy_in: ACCEPT`,
`policy_out: ACCEPT`, and disabled DROP rules. A caller must pass
`pve_firewall_confirm=yes` before even the default-off file is written. CI's
service detector only turns paths below `services/<tier>/<service>/` into
deploy names, and no workflow, `deploy.yml`, or aggregate playbook references
this playbook.

The allowlists preserve the CI runner and jump host on SSH, both subnet router
addresses on SSH and UI, node-to-node SSH and UI, and Prometheus on `:9100`.
The UI allowlist also keeps every non-human `:8006` client found in the repo:
Caddy (`10.0.1.10`, which proxies the `pve1`-`pve3` routes), Uptime Kuma
(`10.0.1.20`, HTTP monitors on each node), and the CI runner (Terraform's
bpg/proxmox provider endpoint is `https://10.0.0.10:8006/`). Anything that
runs Terraform from a LAN workstation needs that workstation in the extra admin
sources.
The operator must add a direct LAN workstation address through
`pve_firewall_extra_admin_sources` when applicable. Omitting it can remove the
operator's direct SSH and UI path.

Proxmox reserves the `management` IPSet for built-in management rules. The
template defines it with the UI sources, including extra admin sources, rather
than allowing Proxmox to fall back to the whole cluster network. In Proxmox's
generated host input chain, the host and cluster `[RULES]` are evaluated first,
then the built-in ACCEPTs for the `management` set (22, 8006, 5900-5999, 3128),
then `policy_in`. With `policy_in: ACCEPT` and the DROP rules disabled, Stage 1
is therefore expected to change no access at all: every packet that misses an
explicit or built-in ACCEPT still hits the ACCEPT policy. The narrowed
`management` set only becomes load-bearing if `policy_in` is ever set to DROP,
which this design never does. This ordering is from Proxmox's firewall
implementation as documented, not observed on this cluster, so the runbook
still requires an independent console and a `pve-firewall compile` review
before Stage 1. Each node's host firewall also needs its normal host-level `enable: 1` for
cluster host rules to take effect; this is expected to be the Proxmox default
but is unverified here.

Corosync UDP 5405 through 5412 and other cluster traffic remain untouched
because both default policies are ACCEPT and no rule targets those ports. The
Terraform LXC module does not set `firewall = true` on container NICs, and this
playbook writes no CT `.fw` files. Enabling the cluster firewall therefore does
not opt containers into firewalling; a CT firewall remains off unless its own
`.fw` configuration also sets `enable: 1`.

### AI agent SSH

`tag:ai-agent` replaces `tag:legacy-agent`, which had been created in the admin
console and would have been deleted by the next GitOps apply. An agent gets
`tcp:22` to three destinations only: the operator's Mac by its stable
Tailscale IP, the CI runner (`10.0.1.13`), and the jump host
(`10.0.1.22`). Everything else in the fleet is reached by SSH-hopping from
the jump host, which already holds fleet keys. That keeps the tailnet ACL from
ever giving an agent a direct path to Proxmox, the NAS, or a service port, and
puts every agent session through hosts whose own `authorized_keys` and logs
are the control point. The agent tag is not on the `autogroup:internet`
grant, so an agent device cannot use the exit nodes.

`tag:legacy-agent` remains in `tagOwners`, the grant, and the tests with
identical access, only so the existing device keeps working when this file is
applied. Rollout: merge; retag the device `tag:ai-agent` (admin console,
Machines, Edit ACL tags, or `tailscale up --advertise-tags=tag:ai-agent` on
the device); confirm SSH to the three hosts; then remove `tag:legacy-agent` in a
follow-up PR.

### Subnet route evaluation

Three route advertisements were considered:

1. Keep one IPv4 `/22` on both routers. This is simplest and preserves full
   fallback reach, but the Pi retains a route to every tier and route status
   cannot show a tier independently.
2. Advertise four `/24` routes on LXC 116, and only infra
   `10.0.0.0/24` plus core `10.0.1.0/24` on the Pi. This reduces the
   fallback router's blast radius while keeping recovery access to Proxmox,
   DNS, monitoring, and control services. `tailscale status` also exposes each
   tier route separately.
3. Narrow further by removing test or advertising selected `/32` routes. This
   minimizes routed address space, but creates a fragile per-host route list
   that must change whenever a service moves or is added.

Choose option 2 for a later change. ACL grants already enforce destination
CIDRs regardless of route advertisement shape, so splitting routes does not
create identity isolation. Its value is smaller Pi blast radius and clearer
route state. Its cost is synchronizing more route entries across primary and
fallback configuration. The existing `/22` auto-approver already approves
contained `/24` routes, so no `autoApprovers` edit is needed.

PR #59 (merged 2026-10-18) last touched these gateway files, so build the
route change on top of it. Update in this order:

1. `services/core/tailscale/docker-compose.yml`: replace the IPv4 `/22` in
   `TS_ROUTES` with all four tier `/24`s and retain the IPv6 `/64`.
2. `services/core/tailscale/raspberrypi-setup.md`: advertise only infra and
   core IPv4 `/24`s on the fallback.
3. `ansible/playbooks/raspberrypi-setup.yml`: add the same fallback route
   arguments so bootstrap and documentation cannot drift. Today this playbook
   enables forwarding but does not run `tailscale up`.

After each router changes, verify the admin console route view or run
`tailscale status --json | jq '.Peer[] | select(.Tags) | .PrimaryRoutes'`.
From an admin device, ping or curl one real host in each advertised tier.
Rollback by restoring the previous `TS_ROUTES` or Pi `--advertise-routes`
value and bringing the affected Tailscale stack or service up again.

## Consequences

### Positive

- Admin access is unchanged: every protocol and port in the former IPv4 `/22`
  and IPv6 `/64` remains granted, now with regression tests.
- Viewer is useful for web and DNS access without direct SSH, Proxmox,
  monitoring, or test access, and assigning it removes no existing access
  because no device currently carries the tag. Apps behind Caddy (including
  the Proxmox UI routes) stay reachable at the HTTP layer, gated by their own
  auth.
- Gateway tags are pinned as routing identities, not privileged pivot sources.
- The firewall configuration, backup path, staged commands, verification, and
  rollback are reviewable before the live firewall is enabled.

### Negative / risks

- Merge still applies `policy.hujson` live. A syntax error or omitted admin
  destination could lock out remote recovery, so both local validation and the
  GitOps policy test must pass before merge.
- A wrong router IP in the host firewall rejects all users behind that router
  because SNAT collapses their identities to one source address.
- A missing workstation IP in the allowlists blocks direct LAN SSH and UI as
  soon as Stage 2 enforces the DROP rules. Stage 1 is expected to be
  access-neutral, but that is unverified live, so console access is required
  for every enablement, not only Stage 2.
- `policy_in: ACCEPT` deliberately leaves ports other than 22, 8006, and 9100
  unchanged. This is host-management hardening, not LAN tier segmentation.
- Proxmox `management` IPSet and simulation behavior are not live-verified in
  this change. The runbook labels that uncertainty and requires observation
  before enforcement.
