---
title: "2026-04-17: Nextcloud OIDC issuer mismatch"
sidebar_position: 1
---

# 2026-04-17: Nextcloud OIDC issuer mismatch

**Severity:** Low (single-user homelab, OIDC login only)
**Duration:** ~1 hour from first symptom to resolution
**Affected:** Nextcloud OIDC SSO via Authentik (`auth.example.com`)

## Summary

After renaming the Authentik public hostname from `authentik.example.com`
to `auth.example.com` and reworking the Caddy config to publish
auth/immich/nextcloud through the Cloudflare tunnel, Nextcloud's OIDC
login broke with **"Access forbidden: The issuer does not match the one
from the discovery endpoint."**

Root cause was two compounding bugs: (1) Caddy's `http://` site blocks
weren't forwarding `X-Forwarded-Proto`, so Authentik built `http://`
URLs in the OIDC discovery doc; (2) `user_oidc` cached that broken
discovery doc for an hour, so even after Caddy was fixed Nextcloud still
compared a stale `http://...` issuer to the fresh `https://...` `iss`
claim in the ID token.

## Impact

- OIDC login to Nextcloud unavailable.
- No data loss, no other services affected.

## Timeline (UTC)

- **05:25**: Caddyfile updated to add `auth.example.com` (replacing
  `authentik.example.com`) and to expose auth/immich/nextcloud over
  `http://` blocks behind the Cloudflare tunnel.
- **05:29**: First failed Nextcloud OIDC attempt; logged as a 502 from
  Cloudflare (Caddy redirect loop on the freshly-deployed http blocks).
- **~06:00**: `header_up X-Forwarded-Proto https` added to all three
  `http://` blocks; Caddy redeployed. Discovery now returns `https://`
  URLs when curl'd directly. Immich OIDC starts working.
- **06:25**: Nextcloud OIDC still failing with issuer-mismatch even
  though discovery is fixed. Debug logging enabled on `user_oidc`;
  `LoginController.php:526` confirms the ID token's `iss` does not
  equal `discovery['issuer']`.
- **06:35**: Identified that `DiscoveryService` in `user_oidc` caches
  the discovery doc for 1 hour. Restarted `nextcloud-app` to flush APCu.
- **06:36**: Login succeeds.

## Root causes

### 1. Missing `X-Forwarded-Proto` on Caddy `http://` blocks

When Cloudflare's tunnel forwards a request to Caddy on port 80, Caddy
in an `http://` site block does not set `X-Forwarded-Proto: https` by
default. Authentik then thinks the original request was plain HTTP and
builds discovery URLs as `http://auth.example.com/...`.

**Fix:**

```caddy
http://auth.example.com {
    reverse_proxy 10.0.0.22:9000 {
        header_up X-Forwarded-Proto https
    }
}
```

Same change applied to `immich` and `nextcloud` http blocks.

### 2. Stale `user_oidc` discovery cache

`OCA\UserOIDC\Service\DiscoveryService::obtainDiscovery()` caches the
fetched OIDC discovery doc via Nextcloud's `ICache` for 1 hour. The
cache was first populated _during the broken window_ with `http://...`
URLs. After Caddy was fixed, Authentik issued fresh ID tokens with
`https://auth.example.com/application/o/nextcloud/` as `iss`, but
`user_oidc` was still comparing against the cached `http://...` issuer.

**Fix:** restart `nextcloud-app` (APCu cache lives in php-fpm process
memory; container restart flushes it).

## Detection

User-reported. There was no Nextcloud-side log entry for the issuer
check until debug logging was enabled; the 403 is rendered as a
template response and only logs at `debug` level
(`LoginController.php:527`). The Authentik side logged the auth flow
as successful, which made it look like Authentik was fine.

## Resolution

- [services/core/caddy/Caddyfile](https://github.com/IanCou/Hyades/blob/main/services/core/caddy/Caddyfile):
  added `header_up X-Forwarded-Proto https` to every `http://` block.
- `docker restart nextcloud-app` on LXC 212 to flush the discovery cache.

## Why Immich wasn't affected

Immich was set up _after_ the Caddy fix, so it never cached a broken
discovery doc. Its OAuth client (`openid-client` for Node) also doesn't
persist discovery between requests by default.

## Lessons / action items

- **Any new `http://` block in Caddy that fronts a tunnel-published
  service MUST set `X-Forwarded-Proto https`.** Otherwise upstream
  apps that build absolute URLs (Authentik, Nextcloud, anything
  rendering OIDC discovery) will return `http://` URLs that break
  downstream clients.
- **When OIDC config or hostnames change, restart the relying party
  to flush its discovery/JWKS caches.** Don't trust that "it'll
  refresh on its own": `user_oidc` caches for an hour, other clients
  vary.
- LXC DNS still resolves internal hostnames via public DNS →
  Cloudflare → tunnel → Caddy. That added a 502 failure mode during
  the broken window. Tracked separately: point all LXCs at AdGuard
  (`10.0.0.27`) so internal traffic stays on the LAN.

## References

- [user_oidc DiscoveryService source](https://github.com/H2CK/oidc/blob/main/lib/Service/DiscoveryService.php)
- [user_oidc LoginController issuer check](https://github.com/H2CK/oidc/blob/main/lib/Controller/LoginController.php)
- [Caddy reverse_proxy header_up directive](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#header_up)
