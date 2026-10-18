# Architecture Decision Records

This directory captures the **why** behind the homelab's design: the trade-offs
that were weighed, the options that were rejected, and the consequences accepted.
The infrastructure code says _what_ runs; these records say _why it runs that way_.

## What an ADR is

An Architecture Decision Record (ADR) is a short, immutable document describing a
single architecturally-significant decision: its context, the options considered
with their pros and cons, the option chosen, and the consequences (good and bad).
Once accepted, an ADR is not rewritten; if a later decision overrides it, a new
ADR is added and the old one is marked **Superseded**.

## Why this repo keeps them

- **A small three-node homelab forces real trade-offs**: density vs. isolation,
  convenience vs. blast radius, simplicity vs. resilience. Writing them down keeps
  the reasoning available when the original context has been forgotten.
- **Honest record of risk.** Several choices here (a SPOF node, a root-trusted CI
  runner, plaintext secrets on disk) are deliberate, time-bound trade-offs. The
  ADRs name the risk and the planned exit so the debt is visible, not hidden.
- **A reference artifact.** Each record is self-contained, quantified where
  possible, and can be cited on its own.

## How to add a new one

1. Copy `_template.md` (in this directory) to `NNNN-kebab-title.md`, incrementing
   `NNNN` to the next free number (zero-padded to 4 digits). Note: files prefixed
   with `_` are template/source files and are not published as pages.
2. Fill in every section. Keep options concrete: list real alternatives and give
   each honest pros **and** cons.
3. Set **Status** to `Proposed` until the decision is actually in effect, then
   `Accepted`. If this ADR replaces an older one, set the old one to
   `Superseded by NNNN` and link both ways.
4. Add a row to the index table below.

## Records

| #                                                           | Decision                                                                         | Status                |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------- | --------------------- |
| [0001](./0001-lxc-over-vm.md)                               | Docker-in-LXC over full QEMU VMs for most workloads                              | Accepted              |
| [0002](./0002-caddy-over-nginx-proxy-manager.md)            | Caddy over Nginx Proxy Manager for reverse proxy + TLS                           | Accepted              |
| [0003](./0003-tier-per-node-placement.md)                   | Static tier-per-node placement                                                   | Accepted (revisit)    |
| [0004](./0004-split-dns-with-pi-secondary.md)               | Split-horizon DNS with an off-cluster Pi secondary                               | Accepted              |
| [0005](./0005-self-hosted-runner-trust-model.md)            | Single self-hosted runner with fleet-wide root SSH                               | Accepted (time-bound) |
| [0006](./0006-sops-for-secrets.md)                          | SOPS + age for secrets-at-rest                                                   | Proposed              |
| [0007](./0007-tailscale-acl-route-scoping.md)               | GitOps-managed Tailscale ACLs, scoping subnet-route access from exit-node access | Accepted              |
| [0009](./0009-oci-free-tier-offsite-backup.md)              | OCI Always Free tier as off-site backup destination                              | Proposed              |
| [0010](./0010-least-privilege-tailnet-and-host-firewall.md) | Least-privilege tailnet access and staged Proxmox host firewall                  | Accepted              |
