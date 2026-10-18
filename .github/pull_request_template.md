<!--
Keep it short. The CI (validate / lint / secret-scan) does the heavy lifting;
this template is just for the context CI can't infer.
-->

## What & why

<!-- One or two sentences. What does this change and what problem does it solve? -->

## Type of change

- [ ] New service (`services/<tier>/<name>/`)
- [ ] Change to an existing service
- [ ] Terraform / infrastructure (LXC, VM, network)
- [ ] Ansible (playbook, role, inventory)
- [ ] Edge / routing (Caddy, AdGuard, Tailscale)
- [ ] Docs only
- [ ] CI / tooling
- [ ] Other:

## Affected services / tiers

<!-- e.g. prod/immich, core/caddy; leave blank for docs/infra-only changes -->

## Checklist

- [ ] Ran `make docs` if I touched Terraform inventory or the Caddyfile (network.md is generated)
- [ ] No secrets, tokens, or real `.env` values committed (gitignored `.env` lives on the runner)
- [ ] Ran `make plan service=<name>` locally for affected services and reviewed the diff
- [ ] Updated relevant docs / changelog entry under `docusaurus/docs/`

## Notes for review / rollback

<!-- Anything reviewers should watch for, manual steps, or how to roll back. -->
