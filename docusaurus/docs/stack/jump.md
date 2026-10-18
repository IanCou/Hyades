---
title: Jump Host
sidebar_position: 49
---

# Jump Host

A barebones SSH bastion: LAN-only, no Docker, no service stack. It exists so every LXC
can be reached through a single hop instead of authorizing keys host-by-host. It
deliberately runs nothing else, to keep the attack surface minimal.

Set up with `ansible-playbook playbooks/authorize-jump.yml` (no compose stack). Inventory
group: `bastions`.

IP/LXC: [network.md](../network.md)

## How it works

`authorize-jump.yml` adds the jump host's root SSH public key to `authorized_keys` on
**every other host** (`hosts: all:!jump`). Run it once after provisioning the jump LXC,
or whenever its key changes. Then:

```bash
ssh -J root@jump.example.com root@10.0.1.19   # e.g. grafana
```

Terraform sets `dns_search_domains` (`example.internal`, `example.com`) on this
LXC, so `-J root@jump root@grafana` resolves too, no FQDN needed.

SSH is **key-only** on all LXCs (`harden-ssh.yml` sets `PasswordAuthentication no`), so
the jump key must be distributed before the bastion is useful.

## Keeping this from drifting

A newly-scaffolded LXC doesn't get the jump key until someone re-runs
`authorize-jump.yml` (easy to forget). `scripts/audit_infra.py`'s `jump-access` check
(run daily by `.github/workflows/infra-audit.yml`) SSHes into every `docker_hosts` LXC,
checks for the jump pubkey in `authorized_keys`, and posts to ntfy if any host is missing
it.

```bash
python3 scripts/audit_infra.py --check jump-access
```

## References

- [SSH ProxyJump (`-J`)](https://man.openbsd.org/ssh#J)
- [`authorize-jump.yml`](https://github.com/IanCou/Hyades/blob/main/ansible/playbooks/authorize-jump.yml)
