# 0007. GitOps-managed Tailscale ACLs, scoping subnet-route access from exit-node access

**Status:** Accepted

## Context

Both Tailscale nodes (`services/core/tailscale/docker-compose.yml`, the
primary; `services/gateways/tailscale/docker-compose.yml`, the Raspberry Pi
fallback) advertise `TS_ROUTES=10.0.0.0/22` and `--advertise-exit-node`.
Confirmed live via `tailscale status --json` on the primary node:
`AllowedIPs` included `10.0.0.0/22`, `0.0.0.0/0`, and `::/0`: the full
LAN subnet plus full internet exit-node routing, both advertised from the
same untagged node.

Checked the live tailnet directly in the admin console (Access controls,
Machines): it was still on Tailscale's **unrestricted default policy**: no
custom ACL rules, no tags on any of the 4 devices (`raspberrypi`,
`vpn-gateway`, an admin laptop, a phone). That meant every device (including
the phone, used purely for exit-node internet routing) had the same `/22`
LAN reach as the operator's own admin device.

The ACL policy itself lived only in the Tailscale admin console, with no
history, no review step, and no connection to this repo's git-based change
process, a real gap given everything else here (Terraform, Ansible,
Compose, Caddy, DNS) is managed as code with PR review.

## Options considered

### Option A: Leave as-is

- **Pros:** Zero effort.
- **Cons:** Every tailnet peer gets the same LAN reach as admin devices,
  whether they're using this as an internet exit node or not. No review
  trail for ACL changes.

### Option B: Hand-edit the ACL policy in the admin console

- **Pros:** No new tooling.
- **Cons:** Exactly the problem this repo's whole IaC model exists to avoid:
  an unreviewed, unversioned change to network access control with no diff,
  no history, no rollback beyond Tailscale's own audit log.

### Option C: GitOps-managed policy file + tag-based route scoping (chosen)

- **Pros:** The policy lives in git (`policy.hujson`) like everything else
  here: PR review, diff, history. `tailscale/gitops-acl-action` validates
  every PR (`action: test`) before anything is live, and applies
  automatically on merge to `main` (`action: apply`), the same
  branch-protected path every other change in this repo takes. Tag-based
  grants keep exit-node routing for every device while scoping LAN access to
  explicitly tagged admin devices.
- **Cons:** A new OAuth client (Trust credentials, scoped to `Policy File:
Read+Write` only) and three GitHub secrets (`TS_OAUTH_ID`,
  `TS_OAUTH_SECRET`, `TS_TAILNET`) to manage. One more credential with
  standing API access to the tailnet, alongside the CI runner's SSH key and
  vault password (see [ADR 0005](./0005-self-hosted-runner-trust-model.md)),
  though scoped narrowly to the policy file only, not the fleet.

## Decision

**Option C.** `policy.hujson` at the repo root is now the source of truth:

```jsonc
{
  "tagOwners": {
    "tag:homelab-gateway": ["autogroup:admin"],
    "tag:homelab-admin": ["autogroup:admin"],
  },
  "grants": [
    { "src": ["tag:homelab-admin"], "dst": ["10.0.0.0/22"], "ip": ["*"] },
    { "src": ["autogroup:member"], "dst": ["autogroup:internet"], "ip": ["*"] },
  ],
  "autoApprovers": {
    "routes": { "10.0.0.0/22": ["tag:homelab-gateway"] },
    "exitNode": ["tag:homelab-gateway"],
  },
}
```

`.github/workflows/tailscale-acl.yml` runs `tailscale/gitops-acl-action@v1`:
`test` on PRs that touch `policy.hujson`, `apply` on push to `main`. The
OAuth client used has the `Policy File: Read+Write` scope only; it cannot
touch devices, users, DNS, or anything else in the tailnet.

**Rollout, in order (tags must exist in `tagOwners`, i.e. this PR must merge,
before any device can be tagged):**

1. Merge this PR. The `apply` job pushes `policy.hujson` live, defining
   `tag:homelab-gateway` and `tag:homelab-admin`.
2. Tag `raspberrypi` and `vpn-gateway` as `tag:homelab-gateway` (Machines →
   device → Edit ACL tags in the admin console, or
   `tailscale up --advertise-tags=tag:homelab-gateway` from each node;
   `autoApprovers` above means their existing route/exit-node advertisement
   gets auto-approved once tagged, no manual re-approval needed).
3. Tag the operator's own admin device(s) `tag:homelab-admin`. **Do this
   before relying on the new grants**: an untagged device gets exit-node
   routing only under the new policy, same as everything else.
4. Verify from a non-admin-tagged device (e.g. the phone) that it can still
   exit through the gateway but can no longer reach `10.0.1.x` /
   `.70.x` / `.71.x` directly.

## Consequences

### Positive

- ACL changes now go through the same PR review + CI validation as every
  other change in this repo, instead of being a console edit with no diff.
- Exit-node routing is preserved for every device.
- LAN/`/22` reach is scoped to explicitly tagged admin devices instead of
  every device ever authorized onto the tailnet.

### Negative / risks

- A new OAuth client is a new standing credential with API access to the
  tailnet's policy file, scoped narrowly (policy file only), but still a
  credential to rotate/manage alongside everything in ADR 0005/0006.
- Until step 2/3 above are done, tagging the gateways and the operator's own
  admin device, the live policy technically applies to zero tagged devices:
  the rollout order matters; don't skip tagging the admin device before
  relying on the new grants, or you lose your own LAN access.

## Addendum (2026-07-12)

Tagging the operator's Mac `tag:homelab-admin` (step 2 above) silently broke
its own exit-node access: once a device is tagged, it's no longer part of
`autogroup:member`, and the exit-node grant only named `autogroup:member` as
`src`. Symptom: selecting an exit node blackholed all traffic instead of
routing it: macOS still redirects the default route into the tunnel
regardless of whether a grant backs it, so the failure was silent rather than
a clean rejection. Fixed by adding `tag:homelab-admin` to the exit-node
grant's `src` list alongside `autogroup:member`. Any future tag added to
`tagOwners` needs the same check: does it need to keep using exit nodes, and
if so, is it listed on the `autogroup:internet` grant?

## Update (2026-10-18)

The Raspberry Pi fallback no longer uses
`services/gateways/tailscale/docker-compose.yml` (deleted 2026-07 because the image has
no arm/v6 build). It runs a native apt install configured per
[`services/core/tailscale/raspberrypi-setup.md`](https://github.com/IanCou/Hyades/blob/main/services/core/tailscale/raspberrypi-setup.md)
and documented in [Raspberry Pi Gateway](../stack/raspberrypi-gateway.md). The primary
remains `services/core/tailscale/docker-compose.yml` on LXC 116, now pinned to `v1.104.1`.
Both gateways advertise `10.0.0.0/22`, `fd00:db8::/64`, and an exit node.

The current grants and auto-approvals are:

```jsonc
{
  "grants": [
    {
      "src": ["tag:homelab-admin"],
      "dst": ["10.0.0.0/22", "fd00:db8::/64"],
      "ip": ["*"],
    },
    {
      "src": ["autogroup:member", "tag:homelab-admin"],
      "dst": ["autogroup:internet"],
      "ip": ["*"],
    },
  ],
  "autoApprovers": {
    "routes": {
      "10.0.0.0/22": ["tag:homelab-gateway"],
      "fd00:db8::/64": ["tag:homelab-gateway"],
    },
    "exitNode": ["tag:homelab-gateway"],
  },
}
```

`policy.hujson` remains the source of truth over this snippet.
