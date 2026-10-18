---
title: GitHub runner
sidebar_position: 45
---

# GitHub Actions runner

Self-hosted runner that executes `.github/workflows/ci.yml`'s `validate`/`deploy` jobs on
every push to `main` touching `services/**` or `docusaurus/**`; see
[ADR 0005](../decisions/0005-self-hosted-runner-trust-model.md) for the trust model.

Set up once with `ansible-playbook playbooks/setup-runner.yml` (no compose stack).

IP/LXC: [network.md](../network.md)

## Setup

Installs the runner binary, configures it with a registration token generated from the
PAT (`vault_github_pat`, needs `repo` + `workflow` scopes), and enables the systemd unit.
Labels are default, so jobs target it with `runs-on: self-hosted`.

Has Ansible + Python installed so it can run playbooks against other LXCs over SSH using
`~/.ssh/id_ed25519`.

## Deploy trigger path

```
git push (services/** or docusaurus/**)
  → Actions picks runner
  → checkout + diff HEAD~1..HEAD
  → per changed service: ansible-playbook playbooks/deploy.yml -l <svc>
  → docusaurus changes: ansible-playbook playbooks/docs.yml
```

## References

- [GitHub self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners)
