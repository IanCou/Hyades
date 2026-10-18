---
sidebar_position: 2
---

# IaC and GitOps

The three pillars that make the homelab reproducible: the provisioning chain, the CI pipeline, and the generated-docs system.

## Provisioning: Terraform → Ansible → Docker Compose

Each tool owns one job. Terraform creates the LXCs on a three-node Proxmox cluster; Ansible brings each to a known configuration; Docker Compose runs the service. Workloads are organized into three tiers (`core`, `prod`, `test`), each assigned its own `/24` subnet convention (`.69`, `.70`, `.71`) within `10.0.0.0/22`. Tiers span nodes rather than mapping to single machines: `core` resides on node1, while `prod` spans node1 and node3, and `test` spans node1 and node2 ([AGENT.md](https://github.com/IanCou/Hyades/blob/main/AGENT.md)).

- One reusable Terraform module, [`lxc-docker`](https://github.com/IanCou/Hyades/blob/main/terraform/modules/lxc-docker), provisions an unprivileged LXC with Docker pre-installed. Every service is created from the same module.
- Per-tier Terraform environments: [`core`](https://github.com/IanCou/Hyades/blob/main/terraform/envs/core), [`prod`](https://github.com/IanCou/Hyades/blob/main/terraform/envs/prod), and [`test`](https://github.com/IanCou/Hyades/blob/main/terraform/envs/test).
- Ansible roles and playbooks configure hosts and deploy stacks: [`ansible/`](https://github.com/IanCou/Hyades/blob/main/ansible).
- One Compose stack per service under [`services/<tier>/<name>`](https://github.com/IanCou/Hyades/blob/main/services).

**Trade-offs recorded as ADRs:** Docker-in-LXC over one VM per service ([ADR 0001](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions/0001-lxc-over-vm.md)): LXCs share the host kernel, enabling 29 containers across the cluster while sharing resources efficiently, at the cost of weaker isolation than hardware virtualization. Initial tier-per-node placement ([ADR 0003](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions/0003-tier-per-node-placement.md)) provided a simple convention, but as workloads expanded across nodes, node1 still retained 23 of the 29 containers as a concentrated single point of failure. See [Resilience & Reliability](./resilience) for details.

## CI/CD

One GitHub Actions workflow, [`ci.yml`](https://github.com/IanCou/Hyades/blob/main/.github/workflows/ci.yml), is the only path to production:

- **`deploy`** runs on a self-hosted runner inside the homelab (the cluster has no public ingress, so deploy needs a runner on the LAN). **`validate`**, **`lint`** and **`secret-scan`** run on GitHub-hosted runners, so code from a pull request never executes on the machine that holds fleet-wide SSH access.
- `validate` detects which services changed and checks only those; `secret-scan` runs [gitleaks](https://github.com/gitleaks/gitleaks-action) against the full git history.
- `deploy` fires only on push to `main`, only after the gate jobs pass.
- Branch protection on `main` is configured via [`scripts/setup-branch-protection.sh`](https://github.com/IanCou/Hyades/blob/main/scripts/setup-branch-protection.sh). It requires a pull request, linear history, and `enforce_admins`, while blocking force pushes and branch deletions. The script sets `validate` as the required status check (`strict: true`), while `lint` and `secret-scan` run alongside it on every PR.

The self-hosted runner's trust model (it holds SSH access to every host) is its own documented, deliberately-accepted trade-off: [ADR 0005](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions/0005-self-hosted-runner-trust-model.md).

## Generated docs, no drift

The network documentation is generated directly from code: [`scripts/gen_docs.py`](https://github.com/IanCou/Hyades/blob/main/scripts/gen_docs.py) extracts the LXC inventory and reverse-proxy routes into [`network.md`](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/network.md) from the Terraform environments and the [Caddyfile](https://github.com/IanCou/Hyades/blob/main/services/core/caddy/Caddyfile). CI executes `scripts/gen_docs.py --check` during the `validate` job, failing if tables are out of date or if any service lacks a stack documentation page.

Caddy was chosen over Nginx Proxy Manager specifically because its config is one diffable file, which is what makes generating docs from it possible; NPM keeps config and certs in a database outside the IaC model ([ADR 0002](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions/0002-caddy-over-nginx-proxy-manager.md)).
