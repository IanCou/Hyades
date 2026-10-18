# Runbook: Node Failure

## Symptoms

- Node disappears from Proxmox cluster view
- HA VMs/CTs fail to start or fence

## Immediate Steps

### 1. Verify it's actually down

```bash
# From a healthy node
ping <node-ip>
ssh root@<node-ip>
pvecm status
```

### 2. Attempt remote power cycle

If remote power control is available, power cycle the node and check whether
it rejoins the cluster.

### 3. If node is fenced / HA triggered

Proxmox HA will automatically restart VMs on surviving nodes after the fence timeout.
Check: **Datacenter > HA > Resources** for migration status.

```bash
# Force HA recovery if stuck
ha-manager set vm:<vmid> --state started
```

### 4. If node is physically dead and won't come back

```bash
# Remove dead node from cluster (run on a surviving node)
pvecm delnode <nodename>
```

> Warning: Do this only after confirming the node is permanently gone. Removing an active node splits the cluster.

### 5. Restore quorum with 2 remaining nodes

If quorum is lost (cluster has 3 nodes, one dead, remaining two can't agree):

```bash
# On one of the surviving nodes: DANGEROUS, understand before running
pvecm expected 1
```

## Recovery

- Re-provision node with same hostname and IP
- Rejoin cluster: `pvecm add <ip-of-existing-node>`
- Restore VMs/CTs from backup if they didn't migrate via HA

## Post-Incident

- [ ] Root cause identified?
- [ ] Hardware replaced / firmware updated?
- [ ] Backup jobs re-verified?
