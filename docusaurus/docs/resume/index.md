---
sidebar_position: 1
---

# Resume / Portfolio

A three-node Proxmox cluster run as infrastructure-as-code: Terraform provisions the LXCs, Ansible configures them, Docker Compose runs the services. Every change ships through a CI pipeline (validate, lint and secret-scan, then deploy) before it touches production.

## Skills matrix

| Skill                              | Where                                                                                                                                                                              |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Infrastructure as Code (Terraform) | One reusable `lxc-docker` module provisions every LXC across three tiers ([terraform/](https://github.com/IanCou/Hyades/blob/main/terraform))                                      |
| Configuration management (Ansible) | Roles + playbooks configure hosts and deploy stacks ([ansible/](https://github.com/IanCou/Hyades/blob/main/ansible))                                                               |
| Containerization (Docker Compose)  | One Compose stack per service under `services/<tier>/<name>` ([services/](https://github.com/IanCou/Hyades/blob/main/services))                                                    |
| CI/CD                              | One workflow (validate, lint, secret-scan, deploy), gated by branch protection ([ci.yml](https://github.com/IanCou/Hyades/blob/main/.github/workflows/ci.yml))                     |
| Generated docs, no drift           | `gen_docs.py` renders network tables from Terraform + Caddyfile; CI fails if they're stale ([scripts/gen_docs.py](https://github.com/IanCou/Hyades/blob/main/scripts/gen_docs.py)) |
| Reverse proxy + automated TLS      | Single Caddyfile, automated DNS-01 TLS cert per host via Cloudflare ([Caddyfile](https://github.com/IanCou/Hyades/blob/main/services/core/caddy/Caddyfile))                        |
| Documented trade-offs              | Nine ADRs recording what was chosen, what was rejected, and why ([decisions/](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions))                               |
| Secrets management                 | Gitignored `.env` → runner-only secrets today; SOPS+age proposed as the end state ([secrets & security](./secrets-and-security))                                                   |

## Pages

- [IaC and GitOps](./iac-and-gitops): the provisioning chain, the CI pipeline, and the generated-docs system
- [Secrets & Security](./secrets-and-security): how secrets are stored and scanned, and current network segmentation boundaries
- [Resilience & Reliability](./resilience): single points of failure, current mitigations, and accepted trade-offs
- [Observability](./observability): the metrics/liveness/alerting pipeline
- [Agent-First & AI](./agent-first-and-ai): why the repo is structured to be operated by a coding agent
