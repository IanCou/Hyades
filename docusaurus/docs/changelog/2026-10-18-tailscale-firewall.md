---
title: "2026-10-18: Tailscale ACL tiers and staged Proxmox firewall"
sidebar_position: 0
---

# 2026-10-18: Tailscale ACL tiers and staged Proxmox firewall

Restructured the Tailscale policy without reducing
`tag:homelab-admin` access. Its four IPv4 grants now name infra, core, prod,
and test separately, but their union remains exactly `10.0.0.0/22`; the
existing LAN IPv6 `/64` and explicit exit-node access also remain. Added an
unassigned `tag:homelab-viewer` for prod web, Caddy, AdGuard DNS, and exit-node
use. ACL tests pin representative admin access and viewer/gateway denials.

Brought the console-created `tag:legacy-agent` into the policy file as
`tag:ai-agent`. It gets `tcp:22` only, to the operator's Mac (`100.64.0.2`),
the CI runner, and the jump host, and reaches the rest of the fleet by hopping
from those hosts. `tag:legacy-agent` stays defined with the same single grant
until the agent device is retagged, so applying this file does not orphan it.
Tests pin the three SSH targets open and Proxmox, NAS, prod, and service ports
closed for both tags.

Added `scripts/check_policy.py`, a standard-library HuJSON parser and local
safety check. It validates tag and alias references, host addresses, test
shape, complete admin LAN coverage, and the admin exit-node grant. It is a
local pre-PR check and is deliberately not wired into CI.

Added a manual `ansible/playbooks/pve-firewall.yml` and shared cluster policy
template. The playbook targets Proxmox nodes, requires
`pve_firewall_confirm=yes`, backs up an existing `cluster.fw`, writes through
one node because pmxcfs replicates it, and compiles without restarting. Both
cluster enablement and restrictive drops default off; inbound and outbound
default policies remain ACCEPT. No workflow or aggregate playbook invokes it.

The allowlists preserve runner and jump-host SSH, both Tailscale subnet-router
source IPs, node-to-node management, and Prometheus scraping. The operator's
LAN workstation is intentionally an empty list variable because no source IP
is recorded in the repo. The staged runbook requires a separate console,
verification after each stage, and gives node-local and cluster-wide rollback
commands.

This is not live firewall deployment. Proxmox remains unfirewalled until the
operator performs the runbook. It also does not segment LXC tiers: the module
does not enable NIC firewalls and the playbook writes no CT firewall files.
