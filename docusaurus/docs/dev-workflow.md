# Dev Workflow: Where Playbooks Run

This repo follows a Terraform -> Ansible -> Docker Compose flow. IaC is
authored in git, but the question this doc answers is _where the Ansible
playbooks actually execute_ and where the credentials they need (SSH keys +
the Ansible vault password) live.

Three execution modes exist today or are available:

| Mode                      | Status           | Where it runs          |
| ------------------------- | ---------------- | ---------------------- |
| (a) Laptop                | In use           | Owner's laptop, ad-hoc |
| (b) GitHub Actions runner | In use           | Self-hosted, on push   |
| (c) Semaphore             | Deployed, unused | LXC 115 (10.0.1.14)    |

## (a) Laptop-only (today, for ad-hoc / infra runs)

The owner runs playbooks like `ansible-playbook playbooks/docker.yml -l immich`
directly from the laptop. `ansible/ansible.cfg` points at a relative
`vault_password_file = .vault_password` (gitignored), so the vault password
_and_ the fleet SSH key must sit on the laptop.

| Aspect                  | Assessment                                     |
| ----------------------- | ---------------------------------------------- |
| Where creds live        | Laptop: `.vault_password` + private SSH key    |
| Auditability            | None - no record of who ran what, when         |
| Scheduling              | None - manual only                             |
| Blast radius            | Laptop holds fleet root SSH; theft = full loss |
| Ergonomics              | Fast, familiar, full CLI flexibility           |
| Single point of failure | The laptop itself (and its local secrets)      |

## (b) GitHub Actions self-hosted runner (service deploys)

`.github/workflows/ci.yml`'s `deploy` job runs on `runs-on: self-hosted`. On a push that
touches `services/**` it exports
`ANSIBLE_VAULT_PASSWORD_FILE="$HOME/.ansible_vault_password"` and runs
`ansible-playbook playbooks/deploy.yml -l "$service"` (or
`playbooks/$service.yml` for a few specials, plus `playbooks/docs.yml`).

| Aspect                  | Assessment                                       |
| ----------------------- | ------------------------------------------------ |
| Where creds live        | Runner: `~/.ansible_vault_password` + SSH key    |
| Auditability            | Good - every run is a CI log tied to a commit    |
| Scheduling              | Git-driven (on push); `workflow_dispatch` manual |
| Blast radius            | Large - the single runner holds fleet root SSH   |
| Ergonomics              | Good for happy path; awkward for one-host runs   |
| Single point of failure | The one self-hosted runner                       |

The runner already concentrates fleet-wide root SSH and per-service secrets
(see the design findings on runner blast radius). It is the right tool for
_declarative, commit-driven_ service deploys, but a poor fit for ad-hoc or
scheduled infra playbooks that need parameters or interactive review.

## (c) Semaphore (deployed Ansible UI)

Semaphore is already running at `services/core/semaphore/docker-compose.yml`
on LXC 115. It executes playbooks _on the LXC_, not the laptop, and stores
credentials in its own key store.

| Aspect                  | Assessment                                      |
| ----------------------- | ----------------------------------------------- |
| Where creds live        | Semaphore key store on the LXC (vault+SSH)      |
| Auditability            | Strong - per-task history, output, who/when     |
| Scheduling              | Built-in cron schedules per template            |
| Blast radius            | SSH key scoped in Semaphore; RBAC limits runs   |
| Ergonomics              | Web UI + surveys; less raw than the CLI         |
| Single point of failure | The Semaphore LXC (but backed up / reprovision) |

### What Semaphore adds

- **Task templates** - a named, reusable wrapper around one playbook
  (e.g. "Deploy service", "Install Docker") so runs are consistent.
- **Surveys** - template parameters captured as a form. A `-l <host>` limit or
  an `-e service=immich` extra-var becomes a dropdown/text field instead of a
  memorized CLI flag.
- **Schedules** - cron entries per template for recurring runs
  (e.g. nightly `prometheus.yml` reconcile) with no laptop involved.
- **History / audit log** - every execution records the user, template, output,
  and exit status. This is the audit trail the laptop flow lacks entirely.
- **RBAC** - users and teams with per-project roles, so "can run prod
  playbooks" is a grantable permission rather than "has the laptop".
- **Key store** - the vault password and SSH keys live _in Semaphore_ on the
  LXC. This is the key win: vault-dependent runs no longer require the secret
  on the laptop.

## Recommendation: hybrid

Keep what works and route the risky bits through Semaphore:

1. **Author all IaC in git on the laptop.** Editing Terraform/Ansible/Compose
   and committing needs no secrets and no fleet access. The laptop stays a
   development box, not an execution box.
2. **Keep CI for service deploys.** `ci.yml`'s `deploy` job stays the
   path for commit-driven `services/**` deploys. It is auditable and already
   wired up.
3. **Route ad-hoc and scheduled PROD/infra playbook runs through Semaphore** -
   especially vault-dependent ones (`docker.yml`, `deploy.yml`, `caddy.yml`,
   `prometheus.yml`, `harden-ssh.yml`). These
   are exactly the runs that today force the vault password and root SSH key
   onto the laptop.

This directly addresses two findings. It gets credentials off the laptop (they
move into the Semaphore key store on LXC 115), and it gives the
high-blast-radius infra runs an audit log + RBAC, so they are no longer an
unlogged action taken from whoever holds the laptop. The single self-hosted
runner keeps its narrow, declarative job instead of being the only alternative
to the laptop for _every_ playbook.

| Run type                     | Recommended mode                     |
| ---------------------------- | ------------------------------------ |
| Edit + commit IaC            | Laptop (git only, no secrets)        |
| Commit-driven service deploy | GitHub Actions runner (mode b)       |
| Ad-hoc infra / single-host   | Semaphore template + survey (mode c) |
| Scheduled / recurring run    | Semaphore schedule (mode c)          |

## Concrete setup steps

All paths below are real and relative to the repo root.

1. **Create a Semaphore project** pointing at this repo. In the UI at
   `10.0.1.14:3000`, add a project and a Git _repository_ entry for this
   repo. Set the playbook directory to `ansible/` so templates can reference
   `playbooks/*.yml` and `ansible.cfg` resolves as it does locally.

2. **Register credentials in the key store:**
   - Add an **SSH key** (the fleet root key) so Semaphore can reach the hosts in
     `ansible/inventory/hosts.yml`.
   - Add the **Ansible vault password** as a key-store entry. `ansible.cfg` sets
     a relative `vault_password_file = .vault_password`; either point
     Semaphore's vault secret at that filename or set
     `ANSIBLE_VAULT_PASSWORD_FILE` in the template environment (mirroring what
     the CI job does with `$HOME/.ansible_vault_password`).

3. **Add task templates** for the common playbooks. Each maps to a real file in
   `ansible/playbooks/` and attaches the key-store entries above:

   | Template          | Playbook                           | Survey vars       |
   | ----------------- | ---------------------------------- | ----------------- |
   | Install Docker    | `ansible/playbooks/docker.yml`     | limit (host/grp)  |
   | Deploy service    | `ansible/playbooks/deploy.yml`     | service, tier, -l |
   | Deploy Caddy      | `ansible/playbooks/caddy.yml`      | limit (host)      |
   | Deploy Prometheus | `ansible/playbooks/prometheus.yml` | limit (host)      |

   For "Deploy service", the survey reproduces the CLI usage documented in
   `ansible/playbooks/deploy.yml` (`-l immich`, optionally
   `-e "service=immich tier=prod"`).

4. **Add schedules** to any template that should run recurringly (e.g. a nightly
   `prometheus.yml` reconcile), so no scheduled run depends on the laptop being
   awake.

Once templates exist, the laptop's `.vault_password` and fleet SSH key can be
removed from the laptop for everyday work; ad-hoc and scheduled runs go through
Semaphore, and commit-driven deploys go through CI.
