<!-- markdownlint-disable MD013 MD060 -->

# Contributing

This repo deploys real infrastructure: a merge to `main` triggers the
`deploy` job in [`.github/workflows/ci.yml`](.github/workflows/ci.yml), which
runs after `validate`/`lint`/`secret-scan` pass and deploys the changed
services and docs. To keep `main`
always-deployable, all changes go through a **feature branch → pull request**
flow. Don't commit directly to `main`.

## Workflow at a glance

| Step | What you do                                     | Why                                       |
| ---- | ----------------------------------------------- | ----------------------------------------- |
| 1    | Branch off `main` (`feat/…`, `fix/…`, `docs/…`) | Isolates work; keeps `main` clean         |
| 2    | Commit with `type: subject`                     | Readable history; drives the squash title |
| 3    | Open a PR with `gh pr create`                   | Triggers CI; gives a review surface       |
| 4    | Wait for the `validate` check to pass           | Same gate that guards deploy              |
| 5    | Squash-merge into `main`                        | One tidy commit per change                |
| 6    | Delete the branch                               | Avoids stale-branch clutter               |

## Branch naming

Branch off the latest `main` and prefix by change type:

| Prefix  | Use for                          |
| ------- | -------------------------------- |
| `feat/` | New service, host, or capability |
| `fix/`  | Bug fix or broken config         |
| `docs/` | Documentation-only changes       |

Example: `feat/searxng-stack`, `fix/adguard-compose`, `docs/git-flow`.

## Commit messages

Use a simple [Conventional Commits](https://www.conventionalcommits.org/)
style: a `type: subject` summary line in the imperative mood.

```text
feat: add searxng search stack
fix: correct adguard volume mount
docs: document the branch-protection setup
```

Common types: `feat`, `fix`, `docs`, `chore`, `ci`, `refactor`.

## Pull requests

1. Push your branch and open a PR against `main`.
2. CI runs the **`validate`** job from
   [`ci.yml`](.github/workflows/ci.yml): compose YAML parsing, Caddyfile
   validation, Ansible syntax/lint, Terraform `fmt`/`validate`, and
   `make docs-check`. Branch protection on `main` requires `validate` and
   `lint` to pass (and the branch to be up to date), so the PR can't merge
   until both are green.
3. If the PR touches a service, run `make plan service=<name>` locally to
   dry-run the deploy (`ansible --check --diff`) against the live host;
   nothing is applied. CI deliberately has no dry-run job: it would need the
   self-hosted runner's SSH key and vault password, and no PR code runs
   there (see
   [ADR 0005](docusaurus/docs/decisions/0005-self-hosted-runner-trust-model.md)).
4. Once approved and green, **squash-merge** so each change lands as one
   commit on `main`, then delete the branch.

> `scripts/setup-branch-protection.sh` requires only `validate` by default.
> `ci.yml` also runs `lint` and `secret-scan` on every PR. Set
> `CONTEXTS="validate lint secret-scan"` when running the script to require
> all three checks before merging (see
> [`scripts/setup-branch-protection.sh`](scripts/setup-branch-protection.sh)).

## How this maps to deploy

The same `validate` job runs in two places, so PRs catch problems before
they can reach production:

```text
PR push ──▶ validate, lint, secret-scan ──▶ review ──▶ squash-merge to main
                                                      │
                            push to main triggers ci.yml
                                                      ▼
                  validate + lint + secret-scan ──▶ deploy (changed services + docs)
```

The `deploy` job in `ci.yml` runs on a push to `main` after all three jobs pass,
and only when `validate` detected changed services or files under
`docusaurus/`. It deploys the changed services and docs site as needed.
Generated `network.md` tables must be regenerated with `make docs` before you
push, or `make docs-check` fails the gate.

## Command cheatsheet

```bash
# Start a change
git switch main && git pull
git switch -c feat/my-change

# Work, then commit
git add -A
git commit -m "feat: short imperative summary"

# Publish and open a PR
git push -u origin feat/my-change
gh pr create --fill --base main

# Watch the required check
gh pr checks --watch

# Merge once green, then clean up
gh pr merge --squash --delete-branch
git switch main && git pull
```

## One-time setup

A repo admin runs [`scripts/setup-branch-protection.sh`](scripts/setup-branch-protection.sh)
once to enforce this flow on `main` (require a PR, require the `validate`
check, linear history, no force-push or deletion). See
[Git flow](docusaurus/docs/git-flow.md) for the rationale behind each setting.
