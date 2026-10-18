# Proxmox

## Cluster

| Setting          | Value                                                |
| ---------------- | ---------------------------------------------------- |
| Cluster name     | master-cluster                                       |
| PVE version      | 9.1.9 (kernel 7.0.0-3-pve)                           |
| Quorum votes     | 3 (quorate)                                          |
| Corosync network | 10.0.0.0/22 (node1: `vmbr0` on `nic0`, gw `.1`)      |
| HA               | Enabled (CRM master node1), no resources managed     |
| Firewall         | Disabled at cluster level (see [Network](./network)) |

## Nodes

| Node  | IP        | DNS                    | Primary role                                |
| ----- | --------- | ---------------------- | ------------------------------------------- |
| node1 | 10.0.0.10 | node1.example.internal | All core LXCs, plus overflow prod/test LXCs |
| node2 | 10.0.0.11 | node2.example.internal | Test/staging workloads                      |
| node3 | 10.0.0.12 | node3.example.internal | Production workloads                        |

Tiers are not pinned to a node; per-LXC placement is in the generated tables
in [Network](./network) (sourced from `terraform/envs/*`).

## QEMU VMs

Unlike LXCs (Terraform-managed), VMs are provisioned ad-hoc via `qm create`.
The inventory lives in [AGENT.md](https://github.com/IanCou/Hyades/blob/main/AGENT.md)
("Current QEMU VM inventory").

For macOS provisioning, follow [macOS VM on Proxmox (OpenCore)](./runbooks/macos-vm).
For cross-node moves: `qm migrate <vmid> <target> --with-local-disks`
(offline if stopped; detach CD media first since `local:iso/...` paths
differ between nodes).

## Storage Pools

| Pool      | Type     | Node(s) | Used for                                                          |
| --------- | -------- | ------- | ----------------------------------------------------------------- |
| local     | dir      | all     | ISOs, snippets, CT templates (`/var/lib/vz`)                      |
| local-lvm | LVM-thin | all     | VM/CT disks (node1: 348 GB thin pool on the OS SSD, 66% used)     |
| nas       | NFS      | all     | `10.0.0.249:/volume1/Ian` (**currently disabled**)                |
| hdd       | dir      | node1   | `/mnt/hdd` (on the root filesystem; no dedicated disk is mounted) |

**Backups:** no vzdump jobs configured as of 2026-10-17 (see
[Backup & restore](./runbooks/backup-restore)).

## Initial Setup Notes

```bash
# Create cluster (run on first node)
pvecm create <cluster-name>

# Join cluster (run on each additional node)
pvecm add <ip-of-first-node>
```

## Useful Commands

```bash
# Cluster status
pvecm status

# Node health
pveperf

# Storage status
pvesm status

# List all VMs/CTs
qm list && pct list
```
