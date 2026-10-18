---
title: "2026-08-02: Home Assistant provisioned (host networking)"
sidebar_position: 6
---

# 2026-08-02: Home Assistant provisioned (host networking)

Provisioned a new prod-tier Home Assistant LXC via
`python3 scripts/new_service.py homeassistant prod node3`, then applied for real:
Terraform, Docker install, compose deploy, Caddy route, and DNS all ran successfully.

| Field | Value                                                                                           |
| ----- | ----------------------------------------------------------------------------------------------- |
| LXC   | 223                                                                                             |
| IP    | 10.0.2.22                                                                                       |
| Node  | node3 (picked over node1 to balance prod-tier load; node1 already carries 6 of 9 prod services) |
| Port  | `:8123`                                                                                         |
| Image | `ghcr.io/home-assistant/home-assistant:stable`                                                  |

## Collision found mid-provisioning

The scaffold was originally cut at vm_id 222 / 10.0.2.21, before noticing another
PR had merged to `main` minutes earlier and already claimed that exact vm_id/IP for real,
applied infrastructure. Caught before any Terraform ran, by comparing this branch's
terraform state against the main checkout's actual `terraform.tfstate` (the other module
was already present at vm_id 222). Rebased onto current `main` and moved
Home Assistant to the next free slot: vm_id 223 / 10.0.2.22. Worth remembering:
`scripts/new_service.py` computes "next free ID" from whatever `main.tf` looks like at
scaffold time; if `main` moves before you apply, re-check before trusting it.

## Networking decision: `network_mode: host`

Every other stack in this repo runs on Docker's default bridge network with a single
port mapping. Home Assistant is a deliberate exception: `network_mode: host`, chosen
after weighing three options (see [the stack page](../stack/homeassistant) for the full
write-up):

- **host** (chosen): Home Assistant's own recommended mode; mDNS/SSDP device
  discovery and HomeKit Bridge work natively. Trade-off: the container shares LXC 223's
  network namespace rather than being NAT-isolated.
- **bridge + `ports: ["8123:8123"]`**: consistent with every other service here, but
  breaks auto-discovery and HomeKit Bridge entirely.
- **macvlan**: gets discovery working with real isolation, but needs its own LAN IP
  outside the tier's addressing scheme, a host-to-macvlan-child shim interface, and
  possibly promiscuous mode on the LXC's vNIC at the Proxmox level.

Caddy's stamped port (scaffold default `8080`) was corrected to `8123`, Home Assistant's
real default.

## Provisioning steps run

1. `terraform -chdir=terraform/envs/prod apply -target=module.homeassistant`: plan
   showed `1 to add, 0 to change, 0 to destroy`, reviewed before applying.
2. `ansible-playbook playbooks/docker.yml -l homeassistant`
3. `ansible-playbook playbooks/deploy.yml -l homeassistant`
4. `ansible-playbook playbooks/caddy.yml`
5. `ansible-playbook playbooks/authorize-runner.yml -l homeassistant`
6. `ansible-playbook playbooks/adguard-rewrites.yml` (dry-run first, then for real):
   added `homeassistant.example.com` (v4 + v6, → Caddy) and
   `homeassistant.example.internal` (→ LXC direct); left every unrelated rewrite
   untouched.

Ran against the main checkout's live Terraform state (the primary clone),
not this worktree; the worktree has no local state of its own, so anything applied
there would have been orphaned once the worktree is cleaned up. The corrected
`main.tf`/inventory/Caddyfile/compose files were staged into the main checkout
temporarily, applied, then reverted. The code itself lands normally through this PR;
only the resulting (gitignored) `terraform.tfstate` was meant to persist there.

## Verification

- `docker ps` on the LXC: `homeassistant   Up` within seconds of deploy.
- Direct: `curl http://10.0.2.22:8123/` → `302` (first-boot redirect to onboarding,
  expected).
- Through Caddy: `curl https://homeassistant.example.com/` → real Let's Encrypt cert
  issued live, routed to the backend. Initially `400 Bad Request` (Home Assistant's own
  reverse-proxy protection, not an infra bug) until `http.trusted_proxies` was appended
  to `configuration.yaml` on the LXC and the container restarted. Now `200`.
- DNS: `dig @10.0.1.16 homeassistant.example.com` → `10.0.1.10`;
  `dig @10.0.1.16 homeassistant.example.internal` → `10.0.2.22`. Both
  correct.
- `.env` (`GENERIC_TIMEZONE=America/New_York`) created directly in the main checkout
  (gitignored; this file is never part of any PR), deployed via `deploy.yml`, and
  pushed to the CI runner via `push-secret.yml` so future CI-triggered deploys keep it.
  `docker exec homeassistant date` confirmed `EDT`.

## Not done

- **Proxmox backup job**: LXC 223 not yet added; do this per
  [backup-restore](../runbooks/backup-restore).
- Onboarding wizard itself (admin account creation): owner action, inside Home
  Assistant's UI.
