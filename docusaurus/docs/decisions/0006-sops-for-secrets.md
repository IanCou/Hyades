# 0006. SOPS + age for secrets-at-rest

**Status:** Proposed

## Context

Service secrets (API tokens (e.g. the Cloudflare DNS token from ADR
[0002](./0002-caddy-over-nginx-proxy-manager.md)), database passwords, admin
credentials) are currently supplied to Compose stacks via `.env` files. Today
those files exist **only on the CI runner** at `/opt/github-runner/envs/*.env`
and are deliberately **not committed to git** (the repo ships `.env.example`
templates instead).

That keeps secrets out of version control, but it has real gaps:

- **No history, no backup, no review.** The only copy of a secret is on one LXC's
  disk (LXC 114). If the runner is lost, the secrets are lost; there is no audit
  trail of what changed.
- **Concentrated exposure.** Per ADR [0005](./0005-self-hosted-runner-trust-model.md),
  the runner already has fleet-wide root. A compromise of that one host also yields
  every secret in **plaintext** on disk.
- **Drift.** A secret value and the code that consumes it live in two different
  places, so they can fall out of sync with nothing to catch it.

The goal is to commit secrets to git **encrypted**, so they get the same history,
review, and backup as the rest of the IaC, without ever storing plaintext in the
repo.

## Options considered

### Option A: Status quo (plaintext `.env` on the runner)

- **Pros:** Zero tooling; works today. Secrets never touch git.
- **Cons:** Single unbacked, unversioned, unreviewed copy on a fleet-root host.
  Plaintext at rest. No history or rollback. (The problem being solved.)

### Option B: SOPS + age, encrypted secrets in git (proposed)

- **Pros:** Secrets live in the repo **encrypted**: full history, review, and
  backup, with plaintext never committed. `age` keys are simple (no GPG keyring,
  no KMS dependency). SOPS encrypts only values, so diffs still show _which_ keys
  changed. CI decrypts at deploy time with a key held only on the runner.
- **Cons:** New tooling to learn and a key-management story (where the age private
  key lives, how it's rotated, how it's recovered). Loss of the private key means
  loss of every secret. The decrypt key still sits on the runner; this shrinks
  the plaintext-at-rest window but doesn't remove runner trust.

### Option C: External secrets manager (Vault / Infisical / cloud KMS)

- **Pros:** Central rotation, fine-grained access policies, audit logging,
  dynamic/short-lived secrets.
- **Cons:** A whole new stateful, highly-available service to run and back up, and
  it would land on the already-saturated node1 (ADR
  [0003](./0003-tier-per-node-placement.md)). Heavy for a single-operator homelab; its
  own availability becomes a new dependency for every deploy.

### Option D: git-crypt

- **Pros:** Transparent encryption; minimal workflow change.
- **Cons:** Encrypts whole files (not values), so diffs are opaque blobs; coarser
  key management and weaker multi-recipient support than SOPS+age.

## Decision

**Proposed:** migrate secrets from plaintext `.env` on the runner to **SOPS-encrypted
files committed to git, using `age` keys**, decrypted by CI at deploy time. Not yet
implemented, recorded as Proposed so the gap and the intended fix are tracked.

SOPS+age is the lightest option that gives version control, review, and backup of
secrets without standing up a new always-on service.

## Consequences

### Positive (once accepted)

- Secrets gain git history, code review, and backup, while staying encrypted at
  rest in the repo.
- Value-level encryption keeps meaningful diffs (which key changed, not the value).
- No new always-on service to operate, unlike a secrets manager.

### Negative / risks

- New key-management responsibility: securely storing, rotating, and recovering the
  `age` private key. Losing it loses every secret.
- The decrypt key still lives on the fleet-root runner, so this **reduces** but does
  not eliminate the ADR [0005](./0005-self-hosted-runner-trust-model.md) exposure.
- Until implemented, the status-quo risks above remain. **Next step:** introduce
  `age` keys, encrypt one stack's `.env` as a pilot, wire SOPS decryption into
  `deploy.yml`, then roll out fleet-wide and move this ADR to Accepted.
