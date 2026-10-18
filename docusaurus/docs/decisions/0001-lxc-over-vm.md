# 0001. Docker-in-LXC over full QEMU VMs for most workloads

**Status:** Accepted

## Context

The cluster is three Proxmox nodes with 8 GB of RAM each (24 GB total). Almost
every workload is a Docker Compose stack: a reverse proxy, a handful of web apps,
monitoring, automation. The question is what to run each stack _inside_: a full
QEMU/KVM virtual machine, or a Proxmox LXC container running Docker.

The driving constraint is memory. A minimal Linux VM reserves its full configured
RAM up front and carries a guest kernel; on 8 GB nodes, paying ~512 MB–1 GB of
overhead per service before the application starts is the difference between
running ~17 services on node1 and running five. A couple of workloads genuinely
need full virtualization (macOS Tahoe and Windows 11; see the VM inventory in
`AGENT.md`), so the choice is not all-or-nothing.

## Options considered

### Option A: One QEMU VM per service

- **Pros:** Hardware-level isolation; a kernel exploit in one guest can't reach
  another. Live migration and snapshots are first-class. Works for any OS.
- **Cons:** Full RAM reservation and a guest kernel per service; at ~17 core
  services on node1 the memory overhead alone would exceed the 8 GB node. Slower
  boot, heavier backups (full disk images), more surface to patch.

### Option B: Docker directly on the Proxmox host

- **Pros:** Zero virtualization overhead; one less layer.
- **Cons:** Pollutes the hypervisor with application packages and Docker's
  iptables rules; a bad container can destabilize the node that runs the whole
  cluster. No clean per-service backup/restore unit. Strongly discouraged by
  Proxmox.

### Option C: Docker inside an LXC container (chosen)

- **Pros:** Containers share the host kernel, so overhead is tens of MB, not
  hundreds; this is what makes ~17 services fit on one 8 GB node. Each service is
  still its own backup/restore/migrate unit (`pct`), its own IP, its own
  blast-radius boundary. Provisioned declaratively by the shared
  `terraform/modules/lxc-docker` module.
- **Cons:** Shared kernel means weaker isolation than a VM. Docker-in-LXC needs
  unprivileged-container uid mapping and a few nesting/keyctl tweaks (documented in
  `unprivileged-lxc.md`); NAS bind mounts and the Tailscale TUN device need
  per-LXC config. Can't run a non-Linux guest.

## Decision

Run each service as Docker inside an unprivileged LXC, provisioned by the shared
`lxc-docker` Terraform module. Reserve full QEMU VMs only for workloads that
require a different kernel or full hardware virtualization (macOS, Windows).

The deciding factor is density: the LXC approach is the only one that fits the
service count onto 8 GB nodes while keeping a clean per-service operational unit.

## Consequences

### Positive

- Service density that VMs could not reach on this hardware: node1 alone runs
  ~17 LXCs.
- Every service is a uniform unit: same Terraform module, same Ansible roles, same
  `pct` backup/restore/migrate verbs.
- Fast provisioning and lightweight backups (container rootfs, not full disk
  images).

### Negative / risks

- Shared-kernel isolation: a host-kernel vulnerability is a cluster-wide concern,
  not a single-guest one. Mitigated by unprivileged containers and key-only SSH,
  but accepted as weaker than VM isolation.
- Recurring Docker-in-LXC friction (uid mapping, TUN, bind mounts); each is a
  known gotcha with a documented fix rather than a one-time setup.
- Revisit if a workload needs strong tenant isolation, or if nodes are upgraded to
  enough RAM that per-VM overhead stops being the binding constraint.

## Update (2026-10-17)

node1 and node2 have since been upgraded from 8 GB to 24 GB of RAM; node3 is
still 8 GB (~56 GB cluster total), so the "8 GB node" figures above describe the
hardware at decision time.
The decision still stands: node1's LXC memory limits alone sum to ~44.8 GB, more
than its 24 GB, so adding per-VM reservation and guest-kernel overhead would
still not fit, and density remains the deciding factor.
