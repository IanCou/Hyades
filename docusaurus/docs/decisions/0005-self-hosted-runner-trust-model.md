# 0005. Single self-hosted runner with fleet-wide root SSH

**Status:** Accepted (time-bound; see risks)

## Context

CI/CD runs on one **self-hosted GitHub Actions runner** (LXC 114,
`10.0.1.13`). The pipeline in `.github/workflows/ci.yml` validates, then
deploys by running Terraform and Ansible against the cluster. For Ansible to
configure every host, the runner holds an SSH key trusted as **root on every LXC
and node** in the fleet (`playbooks/authorize-runner.yml` distributes it).

GitHub-hosted runners can't reach the `10.0.0.0/16` LAN, so a self-hosted
runner is effectively required. The open question is the _trust_ it holds, not
whether to self-host. As it stands, one machine can root every host in the
homelab, and its deploy-time secrets live on its own disk (see ADR
[0006](./0006-sops-for-secrets.md)).

## Options considered

### Option A: Single runner, fleet-wide root SSH (chosen)

- **Pros:** One runner deploys anything anywhere: no per-tier runner fleet, no
  privilege-juggling. Matches the Ansible model where the controller reaches all
  hosts. Cheapest to operate for a single person.
- **Cons:** **Large blast radius**: compromise of this one LXC (a poisoned action,
  a leaked key, a bad workflow) means root on the entire fleet. The runner executes
  code from the repo with that trust, so any path to running code on it is a path
  to fleet-wide root.

### Option B: Per-tier runners with scoped keys

- **Pros:** Compromise is contained to one tier; a test-tier runner can't touch
  core. Smaller blast radius per runner.
- **Cons:** Several runners to provision and patch; cross-tier deploys (e.g. Caddy
  in core referencing a prod service) get awkward. More moving parts for one
  operator.

### Option C: Ephemeral / least-privilege runners (per-job, scoped sudo)

- **Pros:** Smallest standing trust: credentials are short-lived and narrowly
  scoped; no long-lived fleet-root key sitting on disk.
- **Cons:** Significant build-out: per-job runner provisioning, a secrets broker,
  and per-playbook privilege scoping. Heavy for this scale.

## Decision

Keep one self-hosted runner with fleet-wide root SSH for now, treating the LXC as a
**high-value asset** to be protected accordingly. Accept the blast radius as a
known, time-bound trade-off rather than design it away today.

The deciding factor is operational cost: scoped or ephemeral runners are the right
end state but a poor use of a single operator's time at the current scale.

## Consequences

### Positive

- One pipeline deploys every tier with no privilege gymnastics.
- Matches the existing Ansible controller-to-fleet trust model exactly.

### Negative / risks

- **Single point of total compromise:** rooting LXC 114 roots the fleet. This is
  the most concentrated risk in the homelab and is recorded here so it stays
  visible, not forgotten.
- The runner holds deploy secrets on disk (ADR
  [0006](./0006-sops-for-secrets.md)); until that migrates to SOPS+age, a runner
  compromise also leaks every secret in plaintext.
- **Mitigations / exit:** key-only SSH everywhere, runner LXC kept minimal and
  patched, deploys gated on the default branch. Revisit toward scoped or ephemeral
  runners if untrusted PRs ever run on it or the fleet grows past easy manual
  review.
- **2026-07-11 update:** `validate` no longer exports the vault password (it
  doesn't need decrypted vars for a syntax/lint check). `plan` (the job that
  actually needs SSH + the vault password on disk) now requires a manual
  `safe-to-plan` label before it runs, instead of firing on every
  `pull_request` automatically. This is a stand-in for GitHub's
  required-reviewer environment protection, which needs a paid plan for
  private repos and isn't available here. Doesn't change the core trade-off
  this ADR accepts (the runner still has fleet-wide root the moment `plan`
  or `deploy` actually execute), but it adds a deliberate human step before a
  compromised dependency in a routine PR gets a free ride to those credentials.
- **2026-10-17 update:** the 2026-07-11 note was wrong on two counts. `validate`
  still exported the vault password, and it ran PR-supplied code
  (`gen_docs.py`, the Caddy Dockerfile) as root on this runner on every
  `pull_request`, with no label gate. The `safe-to-plan` label was also
  bypassable: it stays on the PR, so every later push re-ran `plan` on
  unreviewed commits. Fix: `validate` now runs on GitHub-hosted
  `ubuntu-latest` with a throwaway vault password file, and the `plan` job and
  label are gone (`make plan` locally replaces it). The runner now executes
  only `deploy`, on push to `main`, so it only runs code that was reviewed and
  merged. That matches the trade-off this ADR accepts.
