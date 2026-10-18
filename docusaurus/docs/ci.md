# CI Overview

A single GitHub Actions workflow, [`ci.yml`](https://github.com/IanCou/Hyades/blob/main/.github/workflows/ci.yml),
runs as one "CI" check with four jobs (subtasks). Together they gate changes
before anything reaches the cluster.

- **`validate`**: the deploy gate. Runs on GitHub-hosted `ubuntu-latest`, so
  PR code never touches the self-hosted runner. Must pass before `deploy` ships
  anything. Steps only run for the parts of the tree that changed.
- **`lint`**: formatting/style checks on GitHub-hosted `ubuntu-latest`.
  Must pass before `deploy` runs.
- **`secret-scan`**: gitleaks over the full history on `ubuntu-latest`. Blocks
  changes that introduce credentials.
- **`deploy`**: ships via Ansible from the self-hosted runner. Only runs on
  push to `main`, and only after `validate`, `lint`, and `secret-scan` all
  pass. Pull requests run everything except `deploy`. To preview a deploy
  before merging, run `make plan` locally (see the
  [dry-run runbook](./runbooks/dry-run-deploys)).

Branch protection from `scripts/setup-branch-protection.sh` requires only
`validate` by default. Set `CONTEXTS="validate lint secret-scan"` when running
that script to require all three PR checks; the deploy job always needs all
three jobs to pass.

## Checks

| Job           | Check                    | What it guards / why                                                                                                                            |
| ------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `validate`    | Detect changes           | Computes which services/docs/Caddy/Terraform changed so later steps run only when relevant.                                                     |
| `validate`    | Validate generated docs  | `gen_docs.py --check`: fails if `network.md` tables drifted from Terraform + Caddyfile.                                                         |
| `validate`    | Validate changed compose | Parses each changed compose file as YAML; catches malformed files without a docker/env dep.                                                     |
| `validate`    | Validate Caddyfile       | `caddy adapt` (custom build with cloudflare DNS module): pure syntax check, catches a broken Caddyfile without needing a real Cloudflare token. |
| `validate`    | Validate Ansible         | `ansible-lint` + `--syntax-check` on the playbooks the deploy job actually runs.                                                                |
| `validate`    | Validate Terraform       | `terraform fmt -check` + `validate` per env: catches malformed/unformatted infra.                                                               |
| `lint`        | Prettier (`--check`)     | Consistent formatting of `md`/`yml`/`yaml`/`json`/`js`. Generated `network.md` is ignored.                                                      |
| `lint`        | markdownlint-cli2        | Markdown style (lenient docusaurus-friendly config; `services/` + `ansible/` notes skipped).                                                    |
| `lint`        | actionlint               | Lints the workflow file itself for errors and bad expressions.                                                                                  |
| `secret-scan` | gitleaks                 | Blocks commits that introduce API keys, tokens, or other credentials.                                                                           |

## Dependency updates

[Renovate](https://docs.renovatebot.com) keeps container images current. On a
weekly schedule it scans the compose stacks under `services/**/docker-compose.yml`
and opens PRs that pin floating tags to digests and bump images (minor/patch
updates are grouped into a single PR). Those PRs are ordinary pull requests, so
they flow through the same `validate`, `lint`, and `secret-scan` gates as any
other change before they can merge. Nothing reaches the cluster un-reviewed.

Renovate is configured in [`renovate.json`](https://github.com/IanCou/Hyades/blob/main/renovate.json)
at the repo root. It runs once the [Renovate GitHub App](https://github.com/apps/renovate)
is installed on the repository (or a self-hosted Renovate action is added to the
workflow); no further wiring is needed.

## Running locally

```sh
make lint     # prettier --check + markdownlint (matches the lint job)
make format   # auto-fix in place
```

`make lint` and the `lint` job use the same globs and config (`.prettierrc`,
`.prettierignore`, `.markdownlint.json`), so local results match CI.
