# Raspberry Pi Tailscale gateway

Install Tailscale via native apt, not Docker (the official image has no arm/v6 build). Advertise the same routes as LXC 116's `TS_ROUTES` for HA failover. Keep `--accept-routes=false` so the Pi does not route its own LAN over the tailnet, and `--accept-dns=false` so its resolver stays on local AdGuard.

`tailscale up` resets omitted flags, so always pass the full set. The `tag:homelab-gateway` tag must exist in `policy.hujson` `tagOwners` before advertising it.

```bash
sudo tailscale up \
  --advertise-exit-node \
  --advertise-routes=10.0.0.0/22,fd00:db8::/64 \
  --advertise-tags=tag:homelab-gateway \
  --accept-routes=false \
  --accept-dns=false
```
