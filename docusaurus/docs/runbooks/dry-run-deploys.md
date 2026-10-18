# Runbook: Dry-run a deploy before prod

Added 2026-06-29.

Preview **what a deploy would change** against the live hosts without applying
anything (the homelab equivalent of `puppet agent --noop` / `terraform plan`).
It runs the **real** [`deploy.yml`](https://github.com/IanCou/Hyades/blob/main/ansible/playbooks/deploy.yml)
in Ansible's check mode (`--check --diff`), so the preview can't drift from what
an actual deploy does.

Run it locally with `make plan service=<name>` before you merge. There is no
CI entry point: a CI dry-run needs the runner's SSH key and vault password, and
no PR code runs on the self-hosted runner (see
[CI: no `plan` job](#ci-no-plan-job)).

## How it works

Ansible `--check` mode walks the playbook but makes no changes; `--diff` prints
the before/after of each file. The tasks in `deploy.yml` are all check-safe:

- `file` (create dir) / `copy` (docker-compose.yml, `.env`): report the diff,
  change nothing.
- `community.docker.docker_compose_v2`: reports what it _would_ pull / recreate.

Both entry points pick the playbook the same way the real `deploy` job does: a
service-specific playbook (`playbooks/<service>.yml`, e.g. `caddy.yml`) if one
exists, otherwise the generic `deploy.yml -l <service>`. That keeps the preview
faithful to production.

## Local: `make plan`

```bash
make plan service=immich
```

This connects to the service's host over SSH and prints:

- a unified diff of `docker-compose.yml` (and `.env`, if you have one locally),
- what `docker_compose_v2` would do (pull / (re)create / no-op),
- a `changed=N` line in the play recap.

Nothing is written to the host. Requires the Ansible vault password
(`ansible/.vault_password`) and SSH access to the target, same as a real
deploy. To then confirm a real deploy left the service healthy, use
[`make verify`](#relationship-to-make-verify).

## CI: no `plan` job

Until 2026-10-17 a `plan` job ran this dry-run on labelled PRs and posted the
diff as a sticky comment. It was removed because it ran PR code on the
self-hosted runner, next to the fleet SSH key and the vault password, and a
push after the `safe-to-plan` label was added re-ran it on unreviewed commits.
For a one-operator homelab, running `make plan` locally gives the same diff
without that exposure. See
[ADR 0005](../decisions/0005-self-hosted-runner-trust-model.md).

## Reading the output

- `changed: [host]` with a `--- / +++` block → the compose file (or `.env`)
  differs from what's on the host; that's the change this PR introduces.
- `ok=… changed=0` everywhere → no-op (e.g. a docs-only or comment-only edit).
- A `docker_compose_v2` "would recreate" note → containers would restart on the
  real deploy.

## Limitations

- **Brand-new services**: the deploy dir doesn't exist on the host yet, so the
  compose copy is skipped in check mode and `docker_compose_v2` has nothing to
  diff against. The dry-run is most useful for **changes to existing** services;
  for net-new ones, follow the [new-service runbook](./new-service) and verify
  after the first real deploy.
- **`pull: always`**: in check mode images are not actually pulled, so the
  preview reflects the **currently running** image, not whatever `latest` would
  resolve to at deploy time.
- **Scope**: this covers the Ansible/compose deploy only. Terraform changes
  still apply without a plan gate; see [below](#future-terraform-plan-gating).

## Relationship to `make verify`

They're the two halves of a safe change, on opposite sides of the deploy:

|               | When              | What it does                                                                     |
| ------------- | ----------------- | -------------------------------------------------------------------------------- |
| `make plan`   | **before** deploy | Dry-run: shows what _would_ change. Read-only.                                   |
| `make verify` | **after** deploy  | Smoke test: SSH reachable + containers running + optional HTTP check. Read-only. |

## Future: Terraform plan gating

The dry-run deliberately stops at Ansible/compose. If Terraform changes ever
warrant the same PR-time review, the planned follow-up is to self-host
[Atlantis](https://www.runatlantis.io/), which posts `terraform plan` as a PR
comment and gates `apply`, complementing this dry-run rather than replacing it.
