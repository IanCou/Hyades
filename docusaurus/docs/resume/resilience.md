---
sidebar_position: 4
title: Resilience & Reliability
---

# Resilience & Reliability

Known single points of failure across the cluster, current mitigations, and accepted operational trade-offs.

## node1 is a single point of failure

Workloads are structured into three tiers (`core`, `prod`, `test`). While `core` runs entirely on node1, `prod` and `test` span multiple nodes (`prod` on node1 and node3; `test` on node1 and node2; see [AGENT.md](https://github.com/IanCou/Hyades/blob/main/AGENT.md)). Despite this distribution, **node1 runs 23 of the fleet's 29 Terraform-managed LXCs**, including all core infrastructure (DNS, Caddy, CI runner, SSO, monitoring) and 7 production services on a single node. Losing node1 causes a major cluster-wide outage.

**Mitigation:** Critical network services (DNS and VPN) are duplicated off node1 onto an independent Raspberry Pi gateway ([ADR 0004](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions/0004-split-dns-with-pi-secondary.md)), ensuring remote access and name resolution remain functional if node1 fails.

**Why not fixed today:** Automatic high availability requires shared distributed storage and fencing, which introduces significant operational overhead for a three-node homelab. Key services also depend on node-local bind mounts from the NAS. A planned intermediate step is redistributing stateless core containers across node2 and node3 to reduce concentration on node1.

## The NAS is an unreplicated data SPOF

Immich (photos) and Nextcloud (files) store data on a single Synology NAS, mounted via NFS. RAID on the NAS tolerates single drive failures, but does not protect against chassis failure, site disasters, or volume corruption.

**Direction:** Implement the 3-2-1 backup strategy (3 copies, 2 media types, 1 off-site). [ADR 0009](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions/0009-oci-free-tier-offsite-backup.md) proposes off-site backups using an OCI Always Free instance running Proxmox Backup Server. Currently, [the backup runbook](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/runbooks/backup-restore.md) defines manual `vzdump` and restore procedures without an automated off-site schedule.

## The self-hosted CI runner holds fleet-wide root

The single self-hosted GitHub Actions runner holds an SSH key trusted as root on every host, so compromising that one LXC compromises the fleet ([ADR 0005](https://github.com/IanCou/Hyades/blob/main/docusaurus/docs/decisions/0005-self-hosted-runner-trust-model.md)). Accepted deliberately for a one-person cluster: the alternative (per-tier runners, or ephemeral/scoped credentials) is real infrastructure that isn't worth building yet at this scale. Named as a risk in the ADR specifically so it isn't forgotten, with a stated exit condition: revisit if untrusted PRs ever run on it.

## Inter-tier LAN traffic lacks firewall enforcement

Each tier has an assigned `/24` range on paper, but every LXC interface is configured with a `/22` netmask. Tailscale ACLs scope remote access, but nothing on the local network stops traffic from crossing tier boundaries. See [Secrets & Security](./secrets-and-security) for details.
