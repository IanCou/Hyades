# 0009. OCI Always Free tier as off-site backup destination

**Status:** Proposed

## Context

`backup-restore.md` has two permanently blank rows: "App data (volumes)" and
"VM/CT snapshots" have no tool, schedule, retention, or destination filled in.
`proxmox.md`'s own Backup Schedule table is empty too. Today, if anything ever
does get backed up, it stays on the same physical site as the primary: a
fire, theft, or a UPS/PSU failure taking out the whole rack loses primary and
backup together. There is currently no off-site copy of anything.

Separately, an OCI Always Free tenancy (region `us-ashburn-1`) already exists
with three resources provisioned and confirmed idle:

- `a1-instance`: `VM.Standard.A1.Flex`, 2 OCPU / 12GB (ARM). As of a June
  2026 unannounced Oracle change, this is now the **entirety** of the Always
  Free Ampere allocation (halved from 4 OCPU/24GB); there is no free ARM
  compute headroom beyond what's already running here.
- `ChaffServer`, `db-server`: both `VM.Standard.E2.1.Micro` (1/8 OCPU / 1GB
  AMD), the two Always Free micro slots, both already claimed.
- Block storage: three 47GB boot volumes + one unattached 50GB volume
  (`TestBlock`) = 191GB of the 200GB free-tier cap. ~9GB of free block
  storage headroom remains, not enough to provision anything new.
- Object Storage: 20GB free tier, 0 buckets, completely unused.
- No Autonomous DB, no Load Balancer provisioned.

This repo already solved "how do we admit a new class of device onto the
network without exposing it publicly or hand-editing ACLs"; see
[ADR 0007](./0007-tailscale-acl-route-scoping.md): GitOps-managed
`policy.hujson`, tag-based scoped grants, `tailscale/gitops-acl-action` on
PR/merge. The same pattern extends cleanly to OCI nodes. Also relevant:
`services/core/uptime-kuma` monitors the cluster from inside the LAN only;
there's no vantage point today that would catch "cluster unreachable from
outside" as distinct from "cluster is down."

## Options considered

### Option A: Leave off-site backup unimplemented

- **Pros:** zero effort.
- **Cons:** single-site failure destroys primary and backup together. Both
  runbook tables stay permanently blank.

### Option B: Object Storage only, skip VM/CT snapshots off-site

Use the unused 20GB Object Storage as an `rclone`/`restic` target for
docker-compose app volumes and configs only (Vaultwarden, service configs,
small DBs), reached over HTTPS/S3 API directly, no Tailscale involvement.

- **Pros:** simplest possible first step. Fits the free quota with margin.
  No new compute role, no ACL change, no new day-2 ops surface.
- **Cons:** leaves the "VM/CT snapshots" row and `proxmox.md`'s Backup
  Schedule table blank: no off-site copy of full VM/CT images, only
  app-level data. 20GB doesn't stretch to Immich's photo library or anything
  media-sized.

### Option C: Use all three idle OCI resources, one role each (chosen)

- `a1-instance` (2 OCPU/12GB, the real horsepower here) becomes an off-site
  Proxmox Backup Server datastore host, joined to the tailnet under a new
  scoped tag. Local Proxmox's native PBS remote-sync job pushes incremental,
  deduplicated backups to it. Fills the "VM/CT snapshots" row properly
  instead of approximating it with generic file sync.
- `db-server` (idle micro) hosts a `restic`/`rclone` REST target backed by
  the already-provisioned, currently-unattached 50GB `TestBlock` volume (no
  new storage cost; it's already inside the 200GB free cap). Fills the
  "App data (volumes)" row.
- `ChaffServer` (idle micro) becomes an external Uptime Kuma monitor,
  checking cluster reachability from outside the LAN. Closes the blind spot
  noted above.
- Object Storage (20GB) becomes the tertiary, cheapest copy: a secondary
  `restic` repo or just the most critical config subset, reachable without
  Tailscale at all.
- **Pros:** uses 100% of resources that are already provisioned and sitting
  idle, at zero additional free-tier cost. Native PBS sync gives proper
  incremental VM/CT restore instead of ad hoc file copies. Clears both blank
  runbook tables. Reuses existing patterns (Tailscale GitOps ACL, Uptime
  Kuma) instead of introducing new tooling.
- **Cons:** the most moving parts of the three options. Two VMs that were
  idle now need real day-2 ops: patching, monitoring, PBS version upgrades.
  The OCI account becomes a second cloud identity with its own credential
  surface to secure, mirroring the "one more credential to manage" caution in
  ADR 0007. Still a single provider, single region (`us-ashburn-1`); this
  hedges against site-level failure, not provider-level failure. Oracle's
  unannounced June 2026 free-tier cut is a signal the terms can move again
  without warning.

## Decision

**Option C.** Assign each idle OCI resource a single clear role: PBS
datastore (`a1-instance`), app-volume backup target (`db-server` +
`TestBlock`), external monitor (`ChaffServer`), tertiary copy (Object
Storage), because it's the only option that actually clears both blank
tables using resources already paid for (as $0), and it composes with
infrastructure already built here rather than adding new tooling.

## Consequences

### Positive

- First real off-site (different physical site, different provider) backup
  copy this homelab has had. Closes the single-site-failure gap in Option A.
- Both blank tables (`backup-restore.md`, `proxmox.md`) get filled with a
  real tool, schedule, retention, and destination once implemented.
- External monitoring vantage point that doesn't exist today.
- Zero incremental free-tier cost: every resource used here is already
  provisioned and idle.

### Negative / risks

- Three previously-idle VMs now need patching, monitoring, and upgrade
  attention: new ongoing operational surface for a single operator.
- OCI API keys/IAM become a second credential surface needing the same
  rigor as the existing SOPS/age model (ADR 0006). Not yet decided where
  they live.
- Always Free terms are not a stable SLA (see the June 2026 A1 halving);
  this should never be the _only_ copy of anything genuinely irreplaceable.
- Single OCI region (`us-ashburn-1`): hedges site failure, not provider
  failure.
- **Revisit trigger:** if Oracle further restricts Always Free, or the
  account gets flagged under OCI's idle-account reclamation policy, fall
  back to Option B for the Object Storage leg, or move that leg to a paid
  alternative (e.g., Backblaze B2).

## Implementation sketch (not yet executed; this ADR is Proposed)

1. Add a new scoped tag (e.g. `tag:homelab-backup`) to `policy.hujson`,
   granted only the PBS port and restic REST port from the specific backup
   job's source, narrower than `tag:homelab-admin`, no LAN-wide reach.
2. Extend the existing `tailscale-postprovision.yml` pattern to the three
   OCI hosts via a new Ansible inventory group (they're not Proxmox-managed,
   so not part of the existing node groups).
3. Attach `TestBlock` (50GB, currently unattached) to `db-server`; install
   the restic REST server there.
4. Install Proxmox Backup Server (arm64 build) on `a1-instance`; configure a
   remote-sync job from the local backup target.
5. Point a new Uptime Kuma monitor group at `ChaffServer`, checking cluster
   reachability from outside the LAN.
6. Fill in `backup-restore.md` and `proxmox.md`'s blank tables with the real
   schedule/retention once live.
7. Document OCI credentials in the existing SOPS/age secrets model
   (ADR 0006) rather than a new mechanism.
