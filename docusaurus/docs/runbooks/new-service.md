# Runbook: Adding a New Service

The command-level workflow lives in [`AGENT.md`](https://github.com/IanCou/Hyades/blob/main/AGENT.md) (§ Add a new
service); this is the checklist version. `<tier>` = `core` (load-bearing infra),
`prod` (user-facing), or `test` (non-critical / experimental).

## 1. Provision the LXC (Terraform)

- [ ] Add a `module` block to `terraform/envs/<tier>/main.tf` (`vm_id`, `hostname`,
      `node_name`, `ip_address`). See the [new LXC runbook](./new-lxc).
- [ ] `terraform -chdir=terraform/envs/<tier> apply -target=module.<service>`
- [ ] Add the host to `ansible/inventory/hosts.yml` with `service` and `tier` vars.

## 2. Create the service directory

```text
services/<tier>/<service>/
  docker-compose.yml
  .env.example        # committed: list all required vars, no values
  .env                # NOT committed (gitignored; lives on the runner)
  setup.md            # optional: first-run steps, gotchas
```

Deploy the shared `node_exporter` stack from `services/_shared/node-exporter/`
once on the new host with `ansible-playbook playbooks/node-exporter.yml -l <service>`
from `ansible/`. It does not belong in the service's compose file.

## 3. Networking & DNS

- [ ] Add a reverse-proxy block to `services/core/caddy/Caddyfile`, then
      `ansible-playbook playbooks/caddy.yml`.
- [ ] Ensure the source files define `<service>.example.internal` (and
      `<service>.example.com` if user-facing). Convention:
      `*.example.com` → Caddy, `*.example.internal` → direct LXC IP.
- [ ] From `ansible/`, run `ansible-playbook playbooks/adguard-rewrites.yml` to
      reconcile rewrites derived from Terraform and the Caddyfile via the API.
- [ ] Run `make docs` to regenerate the `network.md` tables (CI fails otherwise).

## 4. Auth (if user-facing)

- [ ] Front it with Authentik forward-auth in Caddy, or configure OIDC/SAML in the app.

## 5. Backup

- [ ] Include the LXC and any bind-mount paths in the backup plan; no scheduled
      backup job is configured yet (see [backup-restore](./backup-restore)).

## 6. Deploy & document

- [ ] `ansible-playbook playbooks/docker.yml -l <service>` then
      `ansible-playbook playbooks/deploy.yml -l <service>` (first time), or just
      `git push` (CI deploys on changes to `services/**`).
- [ ] `ansible-playbook playbooks/authorize-runner.yml -l <service>` so CI can reach it.
- [ ] **Add a stack page** `docusaurus/docs/stack/<service>.md`; the CI doc-coverage
      check fails if a deployed service has none. Match an existing page (e.g.
      [`grafana.md`](../stack/grafana)).
- [ ] Add a dated entry under `docusaurus/docs/changelog/`.
