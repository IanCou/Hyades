# Agent Guidelines

Reference this file at the start of any session working on this repo.

---

## Repo layout

```
terraform/envs/core/      LXC definitions for node1 (core services)
terraform/envs/prod/      LXC definitions for node3 (prod services)
terraform/envs/test/      LXC definitions for node2 (test services)
terraform/modules/lxc-docker/   shared LXC module

ansible/inventory/hosts.yml     all hosts + IPs + service/tier vars
ansible/playbooks/              one playbook per operation
ansible/roles/                  docker, cloudflared, github-runner, portainer-agent

services/core/            Docker Compose stacks for core LXCs
services/prod/            Docker Compose stacks for prod LXCs
services/test/            Docker Compose stacks for test LXCs

docusaurus/docs/          documentation site source (served at /docs/)
  stack/                  one .md per service
  runbooks/               operational procedures
  decisions/              ADRs: the trade-offs behind each major design choice
  changelog/              dated entries, one file per day
  network.md              authoritative IP/subnet reference
  hardware.md             node specs

progress.md               outstanding work only (migration is done)
AGENT.md                  this file
```

---

## IP scheme

All hosts are in `10.0.0.0/22`. By convention each tier gets its own /24
by third octet: `.68` infrastructure (router `.1`, nodes `.10`-`.12`, NAS
`.249`, VMs), `.69` core LXCs, `.70` prod LXCs, `.71` test LXCs. The subnet
says which tier an LXC belongs to, **not** which node it runs on; tiers span
nodes (check `node_name` in `terraform/envs/<tier>/`).

**Authoritative IP table:** `docusaurus/docs/network.md`

Gateway for all LXCs: `10.0.0.1`. Subnet mask on LXC IPs: `/22`.

Tailscale subnet router advertises `10.0.0.0/22`, covering all tiers.

**Tailscale ACL policy is GitOps-managed:** `policy.hujson` at the repo root,
synced by `.github/workflows/tailscale-acl.yml` (`tailscale/gitops-acl-action`,
`TS_OAUTH_ID`/`TS_OAUTH_SECRET`/`TS_TAILNET` GitHub secrets, OAuth client
scoped to `Policy File: Read+Write` only). Edit the file, open a PR; never
hand-edit the policy in the admin console, it'll be overwritten on the next
merge. See [ADR 0007](docusaurus/docs/decisions/0007-tailscale-acl-route-scoping.md).

---

## Current LXC inventory

LXC IDs, IPs, node placement, and reverse-proxy routes: see [`docusaurus/docs/network.md`](docusaurus/docs/network.md), the single authoritative topology reference.

## Current QEMU VM inventory

| VMID | Name          | Node  | Status  | Notes                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ---- | ------------- | ----- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 200  | core-services | node1 | stopped | Legacy VM, 20 GB. Pre-LXC-migration `legacy_vms` group in inventory. Do not run deploy playbooks against it.                                                                                                                                                                                                                                                                                                              |
| 201  | prod-services | node1 | stopped | Legacy, 32 GB. Migrated from node3 → node1 on 2026-05-24 to free local-lvm.                                                                                                                                                                                                                                                                                                                                               |
| 300  | test-services | node1 | stopped | Legacy VM, 32 GB. Pre-LXC-migration `legacy_vms` group in inventory. Do not run deploy playbooks against it.                                                                                                                                                                                                                                                                                                              |
| 401  | macosvm00     | node2 | stopped | macOS Tahoe (26). OpenCore + macrecovery flow. See [`docusaurus/docs/runbooks/macos-vm.md`](docusaurus/docs/runbooks/macos-vm.md).                                                                                                                                                                                                                                                                                        |
| 400  | windowsvm00   | node1 | running | Re-provisioned 2026-07-16 (fresh install, no relation to the pre-07-11 VM). q35/OVMF, TPM v2.0, 4 cores, 8 GB (balloon off), 80 GB scsi0. See changelog.                                                                                                                                                                                                                                                                  |
| 402  | archvm00      | node2 | running | Arch Linux + Xfce4, installed via `archinstall`. 4 cores, 8 GB, 60 GB scsi0, `vga: qxl`. Static IP 10.0.0.46, SSH key + qemu-guest-agent + spice-vdagent configured. Sudo user `ian`. See [runbook](docusaurus/docs/runbooks/arch-vm.md).                                                                                                                                                                                 |
| 403  | ubuntuvm00    | node3 | running | Ubuntu 24.04.4 LTS Desktop (GNOME). 4 cores, 8 GB, 60 GB scsi0, `vga: virtio,memory=64` (plain `virtio`: GNOME's live-session compositor needed the VRAM bump; the installer itself further required `virtio-gl`, which needed `libgl1`/`libegl1` installed on node3). Static IP 10.0.0.47, SSH key + qemu-guest-agent + spice-vdagent configured. Sudo user `ian`. See [runbook](docusaurus/docs/runbooks/ubuntu-vm.md). |

Proxmox nodes: node1=10.0.0.10, node2=10.0.0.11, node3=10.0.0.12
Cluster: `master-cluster` (3 nodes, quorate)
NAS: 10.0.0.249 (Synology DS923+, NFS `/volume1/Ian` → `/mnt/nas` on node1)

---

## Deployment workflow

### Add a new service

**All `ansible-playbook` commands below must run from inside `ansible/` (`cd ansible`
first)**: `ansible.cfg`'s `inventory`/`roles_path`/`vault_password_file` are relative
paths resolved against your current directory, not auto-discovered from the repo root.
Running them from the repo root fails with "No inventory was parsed" / "role not found"
even though the path you typed looks right. `terraform` and `make` commands run from
the repo root as normal.

0. Scaffold steps 1–4 in one shot: `make new-service name=<service> tier=<tier> node=<node>`
   picks the next free LXC id/IP for the tier, stamps a terraform module, an
   inventory row, a placeholder `docker-compose.yml` (single container, port 8080;
   **replace with the service's real image/ports/containers**), a Caddy block (also
   placeholder port, needs fixing), and a stack doc stub, then regenerates
   `network.md`. Steps 1–4 below are what it does; skip to step 5 once you've fixed
   up the placeholders, or do them by hand if the service doesn't fit the single-container
   template.
1. Add a `module` block to `terraform/envs/<tier>/main.tf`
2. Add host to `ansible/inventory/hosts.yml` with `service` and `tier` vars
3. Create `services/<tier>/<service>/docker-compose.yml` (+ `.env.example`)
4. Add Caddy entry to `services/core/caddy/Caddyfile`
5. Prometheus scrape target: nothing to edit. `services/core/prometheus/prometheus.yml.j2`
   renders targets from the inventory, so the host from step 2 is scraped once its tier
   group (`core`/`prod`/`test`) has it and `prometheus.yml` is deployed (CI does that on
   any inventory change). Powering an LXC off needs no edit: the CI deploy job reads
   Proxmox power state and skips (and stops scraping) any guest that isn't running
6. Run `make docs` to regenerate the network.md tables (CI fails if you skip this)
7. Create the real `services/<tier>/<service>/.env` (gitignored; only `.env.example`
   is committed) with actual secret values
8. Run:

   ```bash
   terraform -chdir=terraform/envs/<tier> apply -target=module.<service>

   cd ansible
   ansible-playbook playbooks/docker.yml -l <service>
   ansible-playbook playbooks/adguard-rewrites.yml
   # add "-e adguard_password=<pass>" only if vault_adguard_password isn't already stored
   ansible-playbook playbooks/deploy.yml -l <service>
   ansible-playbook playbooks/node-exporter.yml -l <service>
   ansible-playbook playbooks/caddy.yml
   ansible-playbook playbooks/prometheus.yml
   ansible-playbook playbooks/authorize-runner.yml -l <service>
   cd ..

   make push-secret service=<service>   # copy the .env from step 7 to the CI runner
   ```

9. Confirm it's up: `make verify service=<service> [url=https://<service>.example.com]`

### Deploy a config change to an existing service

```bash
# Pre-flight (optional): dry-run against the live host; shows the diff,
# applies nothing (like `puppet agent --noop`). Also runs on PRs as a comment.
make plan service=<service>

cd ansible
ansible-playbook playbooks/deploy.yml -l <service>
# Caddy changes:
ansible-playbook playbooks/caddy.yml
# Prometheus config changes:
ansible-playbook playbooks/prometheus.yml
# AdGuard rewrite changes:
ansible-playbook playbooks/adguard-rewrites.yml -e adguard_password=<pass>
```

### Special playbooks

| Playbook                      | Use for                                                                                                                                                                                                                                              |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `caddy.yml`                   | Caddy only: syncs full dir (Caddyfile, Dockerfile, .env)                                                                                                                                                                                             |
| `adguard.yml`                 | AdGuard: disables systemd-resolved pre-flight                                                                                                                                                                                                        |
| `prometheus.yml`              | Prometheus: renders `prometheus.yml.j2` from inventory, validates it with promtool, SIGHUP-reloads on change                                                                                                                                         |
| `docs.yml`                    | Docusaurus: rsyncs full docusaurus/ dir, builds on target                                                                                                                                                                                            |
| `openclaw.yml`                | openclaw: syncs full dir (Dockerfile, openclaw.json, .env), builds on target                                                                                                                                                                         |
| `cobalt.yml`                  | cobalt: syncs full dir (Dockerfile.web, .env), builds the web frontend on target from source (upstream ships no image for it)                                                                                                                        |
| `tailscale-postprovision.yml` | Run on node1 after provisioning LXC 116; adds TUN device                                                                                                                                                                                             |
| `uptime-kuma-monitors.yml`    | Creates all Uptime Kuma monitors via API wrapper (idempotent). Pass `-e uptime_kuma_password=<pass>` or store as `vault_uptime_kuma_password` in vault                                                                                               |
| `adguard-rewrites.yml`        | Reconciles AdGuard DNS rewrites from Terraform + Caddyfile via API (idempotent, additive-only). Pass `-e adguard_password=<pass>` or store as `vault_adguard_password` in vault                                                                      |
| `node-exporter.yml`           | Deploys the shared node_exporter stack to one host or all of `docker_hosts`, plus the apt package on `proxmox_nodes`                                                                                                                                 |
| `audit-infra.yml`             | Reconciles live infra (QEMU VMs, orphaned `/opt/services/*` stacks, node_exporter regressions) against git. Read-only, posts to ntfy. Pass `-e ntfy_username=<u> -e ntfy_password=<p>` or store `vault_ntfy_username`/`vault_ntfy_password` in vault |
| `disable-motd.yml`            | Comments out `pam_motd.so` in `/etc/pam.d/{sshd,login}` on every LXC: no more Debian legal boilerplate + `uname` banner on login                                                                                                                     |

### Provision a QEMU VM

No Terraform module exists for VMs; provision ad-hoc via `qm create` on
the target node. Document the result in the VM inventory table above and
in a changelog entry.

- macOS VMs: follow [`docusaurus/docs/runbooks/macos-vm.md`](docusaurus/docs/runbooks/macos-vm.md)
  end-to-end (OpenCore ISO + Apple `macrecovery.py` + raw-disk recovery).
- Before placing a 64 GB+ VM, check `pvesm status` on the target node;
  refuse to put it on a `local-lvm` with `<30 GB` physical free even
  though thin overprovisioning makes it look fine on paper. If tight,
  rebalance via `qm migrate <vmid> <target> --with-local-disks` (offline
  migration is fine for stopped VMs; ~112 MB/s in this cluster).

### Change an LXC IP (without data loss)

```bash
ssh root@<proxmox-node>
pct stop <vmid>
sed -i 's/ip=OLD_IP\/22/ip=NEW_IP\/22/' /etc/pve/lxc/<vmid>.conf
pct mount <vmid>
sed -i 's/OLD_IP/NEW_IP/' /var/lib/lxc/<vmid>/rootfs/etc/network/interfaces
pct unmount <vmid>
pct start <vmid>
```

Then update Terraform, inventory (Prometheus targets follow it), Caddyfile, and AdGuard rewrites.

---

## Key gotchas

- **Pi exit-node DNS is managed by openresolv**: keep both resolvers in `/etc/resolvconf.conf` as `name_servers="127.0.0.1 1.1.1.1"` and set `resolv_conf_local_only=NO`, via `raspberrypi-setup.yml`. Openresolv otherwise drops the public fallback when a local resolver exists; editing only the generated `/etc/resolv.conf` does not persist.

- **Uptime Kuma monitors use internal IPs**: the uptime-kuma LXC uses public DNS, not AdGuard. Internal-only `*.example.com` domains don't resolve to Caddy internally. All non-tunnel monitors use direct `LXC-IP:port` in `setup_monitors.py`; the IPs themselves are pulled from `scripts/gen_docs.py`'s Terraform parser (not hardcoded a second time); only ports/paths/monitor-type stay explicit.
- **SSH is key-only on all LXCs**: `harden-ssh.yml` set `PasswordAuthentication no`. Password SSH will not work.
- **Grafana password only applies on first boot**: `GF_SECURITY_ADMIN_PASSWORD` in `.env` is ignored if the Grafana DB already exists. Reset with: `docker exec grafana-grafana-1 grafana cli admin reset-admin-password <new>`
- **Grafana data dir** must be pre-created and owned by UID 472: `mkdir -p /data/grafana && chown 472:472 /data/grafana`
- **Terraform init needs registry access**: if offline, skip `init` and run `apply` directly if `.terraform/` is already populated.
- **Changing LXC IPs via Terraform = destroy + recreate** = data loss. Always use the SSH method above for running LXCs.
- **Prometheus config needs custom playbook**: `prometheus.yml` is rendered from `prometheus.yml.j2` + inventory, not copied by the generic `deploy.yml`. Use `playbooks/prometheus.yml`; it SIGHUP-reloads Prometheus when the rendered file changes and fails if the reload didn't take.
- **`ci_deploy_skip` inventory group**: hosts the CI deploy job never targets. Child `stopped` is empty in git and filled per run by `scripts/proxmox_power_state.py` from live Proxmox state (any guest not running; also not scraped by Prometheus when CI deploys it). If no Proxmox node answers, the deploy job fails before touching any host. Child `ci_unreachable` = running hosts the runner can't SSH to (the Pi), kept by hand. A failure on any host that is not skipped fails the job, after every service has had its turn.
- **Prometheus data dir** must be owned by UID 65534 (`nobody`). Handled automatically by `playbooks/prometheus.yml`.
- **Tailscale LXC 116** needs two extra lines in `/etc/pve/lxc/116.conf` on node1 for TUN device. Run `tailscale-postprovision.yml` after reprovisioning.
- **NAS mounts for immich/nextcloud** are bind mounts on node1 (`mp0:` in LXC config). If lost after LXC restart, re-add via `pct set 212 -mp0 /mnt/nas/nextcloud,mp=/mnt/nas/nextcloud`.
- **AdGuard rewrites** are managed via `ansible-playbook playbooks/adguard-rewrites.yml` (API-based, derived from Terraform + Caddyfile); do not hand-edit `AdGuardHome.yaml` over SSH anymore. It only adds/corrects entries in its derived set; manually-added entries (e.g. `desktop.example.com`) are left untouched.
- **Caddy deploys** to `10.0.1.10` (inventory). If caddy's IP has changed and inventory is updated, the old IP override trick is: `ansible-playbook playbooks/caddy.yml -e "ansible_host=OLD_IP"`.
- **node_exporter** is a shared stack (`services/_shared/node-exporter/`), deployed once per host via `ansible-playbook playbooks/node-exporter.yml`; it is _not_ embedded in each service's compose file anymore (used to be copy-pasted into every stack; that drifted, e.g. n8n's stack shipped without one). New LXCs get it automatically when you run `node-exporter.yml` against `docker_hosts`; no per-service compose change needed.
- **DNS convention**: `*.example.internal` → direct LXC IP (SSH); `*.example.com` → Caddy (web UI). Both wildcards live in AdGuard rewrites.
- **`local-lvm` is thin-provisioned and easy to overcommit silently**: `pvesm status` "Available" is the _virtual_ free space, but the underlying VG can be much tighter (run `vgs pve` for real free). When adding a 64 GB+ VM, check both. node3 was caught at 67% used with only ~16 GB physical free even though `pvesm` showed 18 GB available; a fresh macOS install would have filled the pool. Rebalance with `qm migrate` before placing big VMs.
- **`qm migrate --with-local-disks` transfers the full allocated size, not just used blocks**: for the 32 GB prod-services migration it copied all 32 GB in 5m10s at 112 MB/s. Plan accordingly. After migration the source LV is removed and target LV is created fresh.
- **OpenCore can't reliably boot recovery from ISO9660 CDs**: `com.apple.recovery.boot/` files inside an `xorriso`-built ISO are ignored by the picker. Convert `BaseSystem.dmg` to raw with `dmg2img` and attach as a virtual disk instead; OpenCore reads the APFS container and adds a "macOS Base System" entry.
- **`qm set <vmid> --args '...'` replaces the whole arg string**: when adding `-device virtio-tablet` to a VM that already has `-cpu Skylake-Client-v4,...`, you must include the existing args. Read first with `qm config <vmid> | grep ^args:`.
- **OpenClaw's `openclaw.json` `meta` key is reserved** for the app's own `lastTouchedVersion`/`lastTouchedAt`/`wizard` bookkeeping; adding a custom field like `meta.note` fails schema validation (`Gateway failed to start: Invalid config ... meta: Invalid input`) and crash-loops the container. Found live provisioning LXC 604. Fix: `docker run --rm -v <state-volume>:/root/.openclaw <image> openclaw doctor --fix` repairs the volume in place; also fix the committed `openclaw.json` so a rebuild doesn't reintroduce it. Put documentation notes in the stack page, not the config.
- **No LXC uses AdGuard as its DNS resolver**: every LXC in the cluster inherits Proxmox's default (an ISP resolver via `/etc/resolv.conf`), not AdGuard (`10.0.1.16`). `*.example.com` internal-only domains (no public Cloudflare route) only exist as AdGuard rewrites, so they resolve on your own machine (which uses AdGuard) but `getaddrinfo ENOTFOUND` from inside any LXC. This is why every internal-to-internal call in this repo (Caddyfile, prometheus.yml, etc.) uses raw IPs, never hostnames. No cluster-wide DNS fix attempted: out of scope, bigger blast radius than one service.
- **`scripts/new_service.py`'s "next free LXC ID/IP" picker only reads the tracked terraform/inventory files, not the live cluster**: it once scaffolded a service at a VMID and IP that were silently already in use by a real, untracked LXC (`appdev00`) that was never added to this repo's Terraform/Ansible. `terraform apply -target=module.<name>` then collided with it: the resulting state had the new module pointing at the real `appdev00` container's ID, though the container's own config (hostname/cores/memory) was never actually overwritten; the apply appears to have errored before making live changes, not silently succeeded. Recovered via `terraform state rm module.<name>` (removes only the state pointer, touches nothing live) and re-verified `pct config 221` was unchanged before reassigning the module to the real next-free VMID/IP. **Before trusting `make new-service`'s picked ID, cross-check against live `pct list`/`qm list` on every node** (or `pct status <id>` / `ping <ip>` for the specific ID it picked); don't assume the tracked files are a complete picture of what's actually running. `appdev00` is now tracked as `module.appdev00` in `terraform/envs/prod/main.tf`, listed in `ansible/inventory/hosts.yml`, and included in `network.md`.

---

## Documentation rules

After any infrastructure change, always update:

1. **`progress.md`**: mark items done, add new TODOs
2. **`docusaurus/docs/changelog/YYYY-MM-DD.md`**: log what changed and why
3. **`docusaurus/docs/network.md`**: if IPs, subnets, or DNS changed
4. **`docusaurus/docs/stack/<service>.md`**: if a service was added, changed, or has new gotchas
5. **`AGENT.md`** (this file): if the LXC inventory, workflow, or gotchas changed

Changelog entries should cover: what changed, why, what files were touched, any gotchas encountered.

---

## Monitoring

- **Grafana**: `https://grafana.example.com` (Node Exporter Full + Proxmox dashboards)
- **Prometheus**: `http://10.0.1.18:9090` (internal only)
- **Uptime Kuma**: `https://uptime.example.com` (HTTP + ping monitors for all services)

`node_exporter` runs on every LXC and Proxmox node at `:9100` (apt package on the nodes and the Pi). Prometheus scrapes every inventory host in `proxmox_nodes`/`core`/`prod`/`test`/`runners`/`gateways` every 15s, minus the `stopped` group (bastions, legacy and desktop VMs have no exporter).

---

## Git conventions

- **Branches**: use `feat/<short-description>` for new features; open a PR against `main`.
- **Commit messages**: human-sounding and to the point. Do **not** add AI co-author trailers (no `Co-Authored-By: Claude`, no "Generated with" lines). The commit author is the human running the change; do not add yourself (the agent) as a contributor.
