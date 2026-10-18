---
sidebar_position: 20
---

# Stage the Proxmox host firewall

This procedure renders a shared Proxmox `cluster.fw`. It is manual-only and
defaults to `enable: 0`. Read [ADR 0010](../decisions/0010-least-privilege-tailnet-and-host-firewall.md)
before running it.

## 0. Pre-flight

Open a recovery console that does not depend on new SSH or `:8006`
connections from the current source. Use a physical or IPMI console on a node,
or keep an already-open root shell on each node. An established SSH session
should survive because Proxmox permits `ESTABLISHED,RELATED`, but do not treat
that session as the only rollback path.

Confirm the source address used for direct LAN administration. The inventory
does not record one. If SSH or the UI is opened directly from a LAN workstation,
pass its fixed IP or DHCP reservation on every apply, for example:

```bash
-e '{"pve_firewall_extra_admin_sources":["<operator-lan-ip>"]}'
```

Replace the bracketed value with the verified source IP; no workstation
address is recorded in this repo.

Confirm each node's `/etc/pve/nodes/<node>/host.fw` has host firewall
`enable: 1`, which Proxmox normally defaults on. The playbook does not write
these node files. This default is not verified on the live cluster in this
change.

## 1. Dry run

From the repository root:

```bash
cd ansible
ansible-playbook playbooks/pve-firewall.yml \
  -e pve_firewall_confirm=yes \
  --check --diff
```

Review the complete diff. The playbook skips backup and compile commands in
check mode and writes nothing.

## 2. Stage 1: enable built-in filtering, keep explicit drops disabled

Keep the independent console open, then run:

```bash
ansible-playbook playbooks/pve-firewall.yml \
  -e pve_firewall_confirm=yes \
  -e pve_firewall_enable=true
```

Add `pve_firewall_extra_admin_sources` from pre-flight when required. Stage 1
enables the firewall and defines the reserved `management` IPSet, but with
`policy_in: ACCEPT` and the three DROP lines disabled it is expected to change
no access (user rules, then built-in management ACCEPTs, then the ACCEPT
policy; see ADR 0010). That expectation is unverified on this cluster, which is
why a console is required. In the `pve-firewall compile` output, confirm the
three `DROP` rules are absent before moving on.

On a node, inspect status and the compiled rules:

```bash
pve-firewall status
pve-firewall compile | less
```

The expected `pve-firewall simulate` form below is not verified against the
installed Proxmox version. Confirm with `pve-firewall help simulate` first:

```bash
pve-firewall simulate --from 10.0.1.13 --to host --dport 22 --protocol tcp
pve-firewall simulate --from 10.0.1.22 --to host --dport 22 --protocol tcp
pve-firewall simulate --from 10.0.1.18 --to host --dport 9100 --protocol tcp
pve-firewall simulate --from <untrusted-lan-ip> --to host --dport 22 --protocol tcp
```

Expect ACCEPT for the runner, jump host, and Prometheus probes. Expect DROP for
the untrusted source on `:22`. If the simulator or compiled rules do not show
that boundary, set `enable: 0` before continuing.

Test real paths:

- From the runner, SSH to one Proxmox node.
- From the operator's Tailscale admin device, open
  `https://10.0.0.10:8006`.
- In Prometheus, confirm all three node targets remain `up`.

## 3. Stage 2: enforce the explicit port drops

Keep the Stage 1 variables and add enforcement:

```bash
ansible-playbook playbooks/pve-firewall.yml \
  -e pve_firewall_confirm=yes \
  -e pve_firewall_enable=true \
  -e pve_firewall_enforce=true
```

Repeat status, compile, simulation, runner SSH, Tailscale UI, and Prometheus
checks. Also confirm the non-human `:8006` clients still work: open
`https://pve1.example.com` (through Caddy) and check the Uptime Kuma
"Proxmox PVE1"-"PVE3" monitors stay green. If Terraform is run from anywhere
other than the CI runner, run a `terraform plan` from there. From an untrusted LAN host, confirm new connections to `:22` and
`:9100` time out. Confirm each rejected attempt appears in
`/var/log/pve-firewall.log` or the node firewall log in the UI at `info` level.

## 4. Roll back

Use the fastest available path first:

1. On an affected node's console, run `pve-firewall stop`. This stops the
   firewall on that node only and does not survive a firewall restart.
2. Disable it cluster-wide with
   `pvesh set /cluster/firewall/options --enable 0`, or edit
   `/etc/pve/firewall/cluster.fw` and set `enable: 0`.
3. Restore a timestamped file from `/root/pve-firewall-backup/` to
   `/etc/pve/firewall/cluster.fw`.
4. Or rerun the playbook with confirmation and its default
   `pve_firewall_enable=false`.

Do not run `pve-firewall start` or `restart` as part of this playbook. Compile
first, verify access at each stage, and retain the console until testing ends.
