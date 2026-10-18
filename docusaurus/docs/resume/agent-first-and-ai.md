---
title: Agent-First & AI
sidebar_position: 6
---

# Agent-First & AI

Infrastructure-as-code designed so AI coding agents and human operators use identical workflows: operational context is tracked in version control, routine workflows are codified as Makefile targets, and CI enforces validation before deployment.

## The three pieces

1. **Curated, persistent context.** [`AGENT.md`](https://github.com/IanCou/Hyades/blob/main/AGENT.md) documents repo layout, IP scheme conventions, the service deployment sequence, and operational gotchas (such as first-boot credentials, UID mapping, and thin-provisioned LVM limits).
2. **A standard loop implemented via `make` targets.** Standard commands (`make plan`, `make verify`, `make new-service`, `make docs`) provide structured interfaces to validate configuration, test services, and generate documentation.
3. **CI validation on pull requests.** Proposed changes submit pull requests subject to branch protection. The `validate`, `lint`, and `secret-scan` jobs must pass before code can merge to `main`.

## The agent loop, as `make` targets

| Target                                  | What it does                                                                                                                                      | Why it matters                                                                           |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `make verify service=<svc> [url=...]`   | Read-only smoke test: SSH reachable → containers running → optional HTTP check of the public route (401/403 count as success: the chain answered) | Validates end-to-end service reachability and container health after deployment          |
| `make new-service name=X tier=Y node=Z` | Picks the next free LXC ID + IP for the tier, stamps every file (Terraform module, inventory row, compose stack, Caddy block, stack page)         | Automates cross-file boilerplate generation across Terraform, Ansible, Compose, and docs |
| `make push-secret service=<svc>`        | Copies a service's gitignored `.env` onto the CI runner where deploy expects it                                                                   | Codifies the one step that can't live in git                                             |
| `make docs` / `make docs-check`         | Regenerates the generated `network.md` tables; `--check` fails CI if they're stale or a service has no stack page                                 | Enforces documentation coverage before a service merges                                  |

## CI protection and deployment controls

- `main` is protected via [`scripts/setup-branch-protection.sh`](https://github.com/IanCou/Hyades/blob/main/scripts/setup-branch-protection.sh): direct pushes are rejected, linear history is required, and force pushes and branch deletions are blocked.
- Pull requests run three GitHub-hosted jobs: `validate` (generated-docs check, compose/Caddyfile/Ansible/Terraform validation), `lint` (Prettier, markdownlint, actionlint), and `secret-scan` (gitleaks). Branch protection requires `validate` (`strict: true`).
- The `deploy` job runs on the self-hosted runner and executes only on push to `main` after `validate`, `lint`, and `secret-scan` complete successfully.
- Automated tools only interact via pull requests; they cannot deploy to production directly or bypass CI checks.

## Renovate: automated dependency management

[`renovate.json`](https://github.com/IanCou/Hyades/blob/main/renovate.json) configures [Renovate](https://docs.renovatebot.com/) for automated image updates across compose stacks: pinned digests, grouped minor and patch bumps, a Monday-morning schedule, and a concurrency limit of 5. Renovate pull requests run the same CI workflow (`validate`, `lint`, `secret-scan`) as manual pull requests before merging to `main`.
