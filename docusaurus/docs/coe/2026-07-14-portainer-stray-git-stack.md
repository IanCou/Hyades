---
title: "2026-07-14: Portainer git-stack ran duplicate Authentik/Tailscale/Vaultwarden for ~2 months"
sidebar_position: 2
---

# 2026-07-14: Portainer git-stack ran duplicate Authentik/Tailscale/Vaultwarden for ~2 months

**Severity:** Medium (no confirmed data exposure, but a password manager was
involved and the detection gap was total; this ran undetected for the
lifetime of the containers)
**Duration:** ~2 months undetected (container creation timestamps), found
incidentally during unrelated IPv6 work
**Affected:** Portainer LXC (10.0.1.12): disk exhaustion, plus stray
duplicate Authentik, Tailscale, and Vaultwarden containers

## Summary

While debugging an unrelated Tailscale/IPv6 routing issue, `docker ps -a` on
the Portainer host turned up five containers that had no business being
there: a full duplicate Authentik stack (`authentik-postgresql-1`,
`authentik-worker-1`, `authentik-server-1`), a duplicate `tailscaled`, and a
**Vaultwarden** instance not referenced anywhere in this repo's documented
architecture. `network.md` assigns Authentik to its own LXC (`.11`) and
Tailscale to its own LXC (`.15`); both of those hosts had healthy,
legitimate, correctly-uptimed copies already running. Everything on the
Portainer host was a stray duplicate.

Two of the duplicate `node_exporter` containers (one crash-looping copy each
of the Authentik and Tailscale sidecars, both losing the port-9100 bind race
against whichever started first) had been crash-looping continuously for
the full two months, writing unbounded, unrotated JSON logs the whole time
(901MB and 848MB respectively), which is what actually filled the disk and
made the host SSH-unreachable via Ansible (`No space left on device`,
couldn't even create Ansible's own temp dir).

Root cause: at some point, Portainer's own "git repository" stack feature
was pointed at this repo (or an earlier version of it) and used to deploy
pieces of `services/core/*` directly onto the Portainer host itself,
completely bypassing the Terraform + Ansible pipeline that's supposed to be
the only way anything gets deployed here. The resulting containers used real
bind-mounted data directories (`/data/authentik/*`, `/data/tailscale`,
`/data/vaultwarden`), not throwaway volumes, so this wasn't a dry test run;
it was a second, live, unmanaged copy of production services sitting
alongside the real ones.

## Impact

- **Disk:** Portainer host hit 100% disk usage, became unreachable via the
  normal Ansible/SSH flow.
- **Duplicate SSO:** a second Authentik instance existed with its own
  Postgres database, disconnected from the one Caddy actually routes to
  (`auth.example.com` → `10.0.1.11`). No evidence it was ever
  reachable from outside the host itself (no Caddy route pointed at it), but
  its mere existence means two divergent copies of identity data existed.
- **Duplicate Tailscale node:** a second `tailscaled` instance was
  authenticated to the tailnet from the Portainer host, under an identity
  separate from the real `vpn-gateway` node. Not confirmed whether it ever
  advertised routes or was used as an exit node. It was removed before that was
  investigated further.
- **Vaultwarden:** a password-manager instance with a small (272KB) SQLite
  database, last modified ~7 weeks prior to discovery. Not referenced in any
  Caddy route or documented service list. Disposition of its data was left
  to the operator's explicit decision rather than assumed safe to delete;
  see [Resolution](#resolution).
- No confirmed external exposure of any of the above: none of it had a
  public DNS record or Caddy route. The real risk was purely "this existed,
  unmanaged, and nothing would have ever told us."

## Timeline (UTC, approximate; reconstructed from container/file timestamps)

- **~2026-05 (exact date unknown):** Portainer git-stack (internally
  "stack #27" in Portainer's own bookkeeping) deployed, cloning
  `services/core/{authentik,tailscale,vaultwarden,adguard,caddy,nginx,...}`
  and `services/prod/{immich,nextcloud}` onto the Portainer host. Only the
  authentik/tailscale/vaultwarden compose files actually resulted in running
  containers; the rest either never started or were separately stopped.
- **~2026-05-23:** Last modification to Vaultwarden's SQLite database
  (per file mtime), the best available signal for "last time anyone might have
  interacted with it," though this doesn't rule out earlier real use.
- **2026-07-14, during unrelated work:** `ansible-playbook playbooks/deploy.yml
-l raspberrypi -e "service=tailscale tier=gateways"` (an unrelated
  Tailscale IPv6-routing change) revealed the Pi's Docker-based Tailscale
  container was crash-looping and had been the whole time. This was a _separate_,
  unrelated finding from this one, but it's what put "check `docker ps -a`
  more carefully across the fleet" on the agenda for the session.
- **Same session, later:** while diagnosing SSH-over-IPv6 reachability to
  AdGuard, `tailscale ping` revealed the Pi was answering for a subnet route
  that the _core_ exit node should have handled; investigating that led to
  checking Portainer's disk (flagged separately by a background agent fixing
  an unrelated AdGuard DNS rewrite bug, which reported `No space left on
device` when trying to reach the Portainer host).
- **Immediately after:** `df -h` on the Portainer host confirmed 100% disk
  usage. `du -sh /var/lib/docker/containers/*` identified two ~900MB and
  ~850MB JSON log files as the cause.
- **Same session:** truncated the oversized logs (~2.5GB reclaimed),
  configured Docker daemon-wide log rotation (`max-size: 10m, max-file: 3`)
  so this can't recur, and ran `ansible-playbook playbooks/node-exporter.yml
-l portainer`, which is already idempotent and designed to remove any
  pre-existing per-service `node_exporter` container before deploying the
  correct centralized one, so it cleaned up all three stray node-exporters
  in one pass.
- **Same session, `docker ps -a` after cleanup:** revealed the _actual_
  duplicate Authentik/Tailscale/Vaultwarden application containers
  underneath the node-exporter noise, the real subject of this writeup.
  Cross-checked against `.11` and `.15` to confirm those hosts had their own
  healthy originals before concluding the Portainer-host copies were
  duplicates, not the source of truth.
- **Same session:** removed the confirmed-duplicate Authentik and Tailscale
  containers plus their data directories. Vaultwarden's removal was
  deliberately held for explicit operator confirmation, since, unlike
  Authentik and Tailscale, no known-good instance exists elsewhere to
  compare it against, so "duplicate" wasn't actually the right word for it.

## Root causes

### 1. Portainer's own stack-deployment feature bypassed the tracked infra pipeline entirely

Every other deployment in this repo goes through
`ansible-playbook playbooks/deploy.yml` (or a service-specific playbook),
which copies the compose file to `/opt/services/<name>/` on the target host.
Portainer's "git repository" stack feature does its own independent thing:
clones the repo (or a URL) directly on the host it's managing, and deploys
via `docker compose` from `/data/portainer/compose/<stack-id>/`, completely
outside `/opt/services/`. There is nothing wrong with Portainer's feature in
isolation; the problem is that this repo's only orphan-detection tooling
(`check_orphaned_services()` in `scripts/audit_infra.py`) only ever looked
at `/opt/services/*`. A deploy that never touches that path is invisible to
it by construction, not by a check that failed. There was no check that
could have failed here.

### 2. No fleet-wide "what's actually running" audit existed, only "what's on disk in one specific path"

The existing `audit-infra.yml` / `audit_infra.py` genuinely does drift
detection (QEMU VM inventory, orphaned `/opt/services/*` stacks,
`node_exporter` regressions), but every check operates on some form of "is
this path/file what git says it should be," never on `docker ps` directly.
Nothing was reconciling _actual running containers_ against _what a host is
supposed to run_, which is the only check that would have caught this
specific failure mode (a deploy mechanism outside the tracked path
entirely).

### 3. No log rotation configured on the Portainer host's Docker daemon

Independent of the duplicate-services issue: this host had no
`/etc/docker/daemon.json` at all, meaning Docker's default `json-file`
logging driver had no size cap. Two crash-looping containers (fighting over
port 9100, see below) spent two months writing the same handful of log
lines in an infinite restart loop, accumulating to ~1.75GB combined before
the disk ran out. This is what actually forced the issue to the surface:
without the disk filling up, the duplicate services might have kept running
unnoticed indefinitely.

### 4. Port 9100 collision masked the real issue as a "crash loop," not "duplicate services"

Three different `node_exporter` sidecars (one bundled with each duplicated
service, from before `node_exporter` was centralized; see
`ansible/playbooks/node-exporter.yml`'s own comment: _"used to be
copy-pasted into every service's docker-compose.yml... a duplicated
liability to audit N times instead of once"_) all tried to bind host port
9100 via `network_mode: host`. Only one could win; the other two
crash-looped forever on `bind: address already in use`. This is what first
drew attention (`docker ps -a` showing `Restarting (1)`), and initially
looked like a simple, boring node_exporter misconfiguration; the actual
duplicate application containers underneath were only discovered because
the fix for the node_exporter symptom (`node-exporter.yml`, which does a
full `docker ps -a` cleanup pass) required looking at full container
listing, at which point the other five stray containers were impossible to
miss.

## Detection

Entirely incidental. No monitoring, alert, or audit check flagged any part
of this (not the duplicate services, not the crash-looping containers, not
the disk filling up) until it happened to block an SSH connection during
unrelated work and someone looked at `docker ps -a` by hand. This is the
same failure pattern the existing `audit_infra.py` module docstring already
names as its whole reason for existing (_"something on disk... silently
diverged from what git/AGENT.md claims, and nothing caught it until someone
SSHed in by hand and looked"_). This incident is a second instance of
exactly that pattern, in a spot the first round of tooling didn't cover.

## Resolution

- Truncated the two oversized (~900MB, ~850MB) container log files to
  reclaim disk space immediately (2.5GB freed, 100% → 75% usage).
- Added `/etc/docker/daemon.json` on the Portainer host with
  `log-opts: {max-size: "10m", max-file: "3"}` and restarted the Docker
  daemon; this bounds every container's logs going forward, host-wide.
- Ran `ansible-playbook playbooks/node-exporter.yml -l portainer`, which
  removed all three stray per-service `node_exporter` containers and
  deployed the correct centralized one in their place. This playbook
  already existed and was already designed to do exactly this cleanup, it
  just hadn't been re-run against this host since the strays accumulated.
- Verified `.11` (Authentik) and `.15` (Tailscale) each had their own
  healthy, correctly-uptimed originals before concluding the Portainer-host
  copies were duplicates.
- Removed the confirmed-duplicate `authentik-server-1`, `authentik-worker-1`,
  `authentik-postgresql-1`, and `tailscaled` containers plus their
  `/data/authentik` and `/data/tailscale` bind-mount data directories, after
  explicit operator confirmation (a permission-classifier check initially
  and correctly blocked the removal pending that confirmation, given the
  blast radius of force-removing stateful containers).
- Vaultwarden's disposition (remove vs. keep) was deliberately left to the
  operator rather than folded into the same "duplicate" cleanup: it isn't
  actually a duplicate of anything documented, so there was no known-good
  original to verify it against the way there was for Authentik and
  Tailscale.

## Prevention: action items

- **Added `check_running_container_drift()` to `scripts/audit_infra.py`.**
  Diffs actual `docker ps` output (via each running container's
  `com.docker.compose.project` label) against the single service each host
  is supposed to run per `ansible/inventory/hosts.yml`. This is the check
  that would have caught this incident on day one: it operates on what's
  _actually running_, not on a specific deploy path that a bypass mechanism
  can simply avoid touching. Hosts that legitimately run a changing set of
  sub-deployments (`coolify`, a PaaS by design) are explicitly exempted
  rather than false-positiving on every app deployed through the platform.
- **Added `.github/workflows/infra-audit.yml`**, a daily scheduled run of
  `playbooks/audit-infra.yml` on the self-hosted runner (`workflow_dispatch`
  also available for on-demand checks). The existing audit tooling was
  correct and suffient in scope for what it checked; it just only ever ran
  when someone remembered to invoke it by hand, which is the same
  "undetected until manually looked at" failure mode this whole incident is
  an instance of. This closes that gap independent of the new check above.
- **Configured Docker log rotation on the Portainer host specifically**:
  worth auditing whether other hosts in the fleet have the same gap
  (no `/etc/docker/daemon.json`, unbounded `json-file` logs). Not done as
  part of this incident; flagged here as follow-up scope.
- Not yet done, worth considering: block or restrict Portainer's own
  git-repository stack deployment feature (or at minimum, document loudly
  that it exists and bypasses the tracked pipeline) so this specific
  mechanism can't silently recreate the same class of incident. The new
  `container-drift` check will _detect_ a recurrence quickly now, but
  doesn't prevent the deploy from happening in the first place.

## References

- [scripts/audit_infra.py](https://github.com/IanCou/Hyades/blob/main/scripts/audit_infra.py)
- [ansible/playbooks/node-exporter.yml](https://github.com/IanCou/Hyades/blob/main/ansible/playbooks/node-exporter.yml)
- [.github/workflows/infra-audit.yml](https://github.com/IanCou/Hyades/blob/main/.github/workflows/infra-audit.yml)
- [Docker log rotation (`json-file` driver options)](https://docs.docker.com/engine/logging/drivers/json-file/)
- [Portainer: Git repository stacks](https://docs.portainer.io/user/docker/stacks/add#option-3-git-repository)
