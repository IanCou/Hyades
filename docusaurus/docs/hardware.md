# Hardware

## Proxmox Cluster Nodes

Three nodes (`10.0.0.10`–`.12`), each an Intel Core i5-8500
(6C/6T @ 3.0–4.1GHz). RAM and disks differ per node (live data, 2026-10-17):

| Node  | RAM                          | Disks                                                                                          |
| ----- | ---------------------------- | ---------------------------------------------------------------------------------------------- |
| node1 | 24 GB DDR4 (23.3 GiB usable) | SanDisk SDSSDH3 512 GB SSD (96 GB root + 348 GB `local-lvm`); WD15EARS 1.4 TB HDD, not mounted |
| node2 | 24 GB (23.3 GiB usable)      | Not documented yet                                                                             |
| node3 | 8 GB (7.5 GiB usable)        | Not documented yet                                                                             |

Cluster total is ~56 GB. node1 and node2 were upgraded from 8 GB; node3 has
not been. node1's DIMMs are mismatched (one 16 GB + one 8 GB, rated 3200 and
2666), so both run at 2666 MT/s. node2's DIMM layout is not documented yet.

## NAS

| Device | Model           | IP         | Protocol | Shares                                                       |
| ------ | --------------- | ---------- | -------- | ------------------------------------------------------------ |
| nas    | Synology DS923+ | 10.0.0.249 | NFS      | immich, nextcloud (Proxmox `nas` storage currently disabled) |

Proxmox storage pools are listed in [Proxmox](./proxmox#storage-pools).

## Notes

- Same CPU on every node, but RAM is not uniform: node3 (8 GB) has no headroom to absorb a failed node's guests
- RAM is still tight on node1 despite 24GB: its Terraform LXC memory limits sum to ~44.8GB, plus the running 8GB Windows VM, so node1 is overcommitted on limits (actual usage is lower). Check real usage with `pvesh get /nodes/<node>/status`
- i5-8500 has Intel UHD 630, available for hardware video transcoding via iGPU passthrough if needed
