# Security Policy

## Supported Scope

This repository contains infrastructure-as-code for a self-hosted
Proxmox homelab (Terraform -> Ansible -> Docker Compose), published as a public
reference project. Security maintenance applies to the
`main` branch only. There are no released versions or backports.

The services defined here are intended to run on a private network behind a
reverse proxy and identity provider; this policy covers the configuration in
this repo, not the upstream software it deploys.

## How Secrets Are Managed

No real secrets are committed to git. Defense in depth is used:

- **`.gitignore`** excludes `secrets/`, `.env`, `*.tfvars`, Terraform state,
  the Ansible vault (`ansible/group_vars/all/vault.yml`), and the vault
  password file (`ansible/.vault_password`).
- **Runner-only env files**: per-service secrets live solely on the CI runner
  at `/opt/github-runner/envs/*.env` and are never tracked in git.
- **Ansible Vault** holds the remaining sensitive variables, encrypted at rest.
- **`.env.example`** files ship with each service and contain only placeholder
  values (for example `FOO=changeme`) to document required keys.
- A migration to **SOPS + age** for encrypted-in-repo secrets is proposed but
  not yet adopted.

## Automated Secret Scanning

CI runs [gitleaks](https://github.com/gitleaks/gitleaks) via the `secret-scan`
job in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) on every push
and pull request. The job checks out full history (`fetch-depth: 0`) and
scans it in one pass; there is no separate fast diff-only job.

The shared [`.gitleaks.toml`](.gitleaks.toml) extends the default ruleset and
allowlists `*.env.example` placeholders and the repo's RFC1918 private IP
addresses so they do not trigger false positives.

Contributors can catch issues before pushing by installing the local
pre-commit hook (see [`.pre-commit-config.yaml`](.pre-commit-config.yaml)):

```sh
pip install pre-commit
pre-commit install
```

## Reporting a Vulnerability

Please report suspected vulnerabilities or exposed secrets **privately**. Do
not open a public issue.

Use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
on this repository: open the **Security** tab, then choose **Report a
vulnerability**.

You can expect an initial response within a few days. If a secret was
committed, it will be rotated and the history scrubbed.
