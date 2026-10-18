# Runbook: Backup & Restore

## Backup Strategy

**Known gap:** No scheduled VM/CT or app-volume backup job is configured yet.
[ADR 0009](../decisions/0009-oci-free-tier-offsite-backup.md) proposes
off-site copies to OCI, including Proxmox Backup Server for VM/CT backups and
restic/rclone for app data. Confirm a backup exists before using the restore
procedures below.

| Layer              | Tool           | Schedule  | Retention | Destination                                                                                        |
| ------------------ | -------------- | --------- | --------- | -------------------------------------------------------------------------------------------------- |
| VM/CT snapshots    | Proxmox Backup |           |           | _planned: off-site PBS on OCI, see [ADR 0009](../decisions/0009-oci-free-tier-offsite-backup.md)_  |
| App data (volumes) |                |           |           | _planned: restic/rclone to OCI, see [ADR 0009](../decisions/0009-oci-free-tier-offsite-backup.md)_ |
| Config repo        | Git            | on change | forever   | GitHub                                                                                             |

## Proxmox VM/CT Backup

The planned scheduled Proxmox job would be configured under **Datacenter > Backup**
in the Proxmox UI. Until then, a single VM/CT can be backed up manually:

```bash
# Manual backup of a single VM (ID 100)
vzdump 100 --storage <storage-pool> --mode snapshot --compress zstd
```

## Restoring a VM/CT

1. In the Proxmox UI: Storage > Backups > select backup > Restore
2. Or via CLI:

```bash
qmrestore <backup-file>.vma.zst <new-vmid>
pct restore <new-ctid> <backup-file>.tar.zst
```

## Docker Volume Restore

```bash
# Stop the stack
docker compose down

# Restore volume from backup
# (adapt path to your backup tool)
tar -xzf backup.tar.gz -C /data/<service>/

# Bring stack back up
docker compose up -d
```
