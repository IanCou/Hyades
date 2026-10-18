---
sidebar_position: 3
---

# Secrets & Security

How credentials are kept out of git, how secret scanning operates, and the current state of network segmentation.

## Secrets management

Secrets have gone through two stages so far, with a third proposed:

1. **Gitignored `.env` files.** `.gitignore` excludes `secrets/`, `.env`, `*.tfvars`, Terraform state, and the Ansible vault. Each service ships a `.env.example` with placeholder values so required keys are documented without leaking real ones.
2. **Runner-only env files.** Real secrets live in exactly one place (the CI runner at `/opt/github-runner/envs/*.env`), never tracked in git. `make push-secret service=<name>` automates copying a local `.env` to the runner via an [Ansible playbook](https://github.com/IanCou/Hyades/blob/main/ansible/playbooks/push-secret.yml), instead of a manual `scp`.
3. **Proposed: SOPS + age.** [ADR 0006](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions/0006-sops-for-secrets.md): encrypt secret values, commit the ciphertext to git (versioned, reviewable, survives a runner rebuild), decrypt at deploy time with an `age` key only the runner holds. Chosen over HashiCorp Vault (no new always-on service to run on an already-saturated node) and git-crypt (which encrypts whole files, so diffs can't show which value changed). Not yet implemented; the runner still holds plaintext today.

## Secret scanning

CI runs [gitleaks](https://github.com/gitleaks/gitleaks) in a dedicated `secret-scan` job on every push and PR, checking out full git history (`fetch-depth: 0`) so a credential committed weeks ago is still caught, not just new diffs. A shared [`.gitleaks.toml`](https://github.com/IanCou/Hyades/blob/main/.gitleaks.toml) allowlists `.env.example` placeholders and the repo's private IPs so they don't fire as false positives. The same check runs locally as a pre-commit hook for faster feedback, with CI as the check that can't be skipped.

## Network security

- **Split-horizon DNS via AdGuard.** `*.example.com` resolves to Caddy (TLS, proxied); `*.example.internal` resolves to the direct LXC IP (SSH, non-proxied access). Both wildcards live in AdGuard rewrites.
- **Off-cluster Raspberry Pi gateway.** A standalone Pi runs a second AdGuard + Tailscale, independent of Proxmox. Without it, a full cluster power-off would take down DNS and VPN at exactly the moment you need them to get back in and fix things. The Pi breaks that circular dependency ([ADR 0004](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions/0004-split-dns-with-pi-secondary.md)).
- **Key-only SSH.** `PasswordAuthentication no` fleet-wide, verified live.
- **Tailscale ACLs are GitOps-enforced and tested.** Remote access policies are managed in [`policy.hujson`](https://github.com/IanCou/Hyades/blob/main/policy.hujson) and applied via [`.github/workflows/tailscale-acl.yml`](https://github.com/IanCou/Hyades/blob/main/.github/workflows/tailscale-acl.yml). Devices tagged `tag:homelab-admin` retain full LAN access, expressed as four per-tier `/24` grants whose union is the original `10.0.0.0/22`; standard devices retain exit-node internet routing only. An opt-in viewer tag permits prod web, Caddy, and DNS without direct SSH or management-port access ([ADR 0010](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions/0010-least-privilege-tailnet-and-host-firewall.md)).
- **LAN tier segmentation is still unfirewalled.** Every LXC interface uses a `/22` netmask, and local LAN traffic between tiers currently lacks Proxmox firewall rules. A manual host-management ruleset is staged, default off, in [`ansible/playbooks/pve-firewall.yml`](https://github.com/IanCou/Hyades/blob/main/ansible/playbooks/pve-firewall.yml); it is not deployed and does not enable CT firewalls. Implementing intra-LAN firewall rules between tiers remains the network isolation task.
