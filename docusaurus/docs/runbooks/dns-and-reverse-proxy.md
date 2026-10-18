# Runbook: DNS and Reverse-Proxy Edits

How to add or change an internal DNS record (AdGuard rewrite) and a public
reverse-proxy route (Caddy). Run these from the repo root unless a
step says otherwise.

## DNS naming convention

`<svc>.example.com` resolves to Caddy (`10.0.1.10`, fronts TLS; use
for web UIs); `<svc>.example.internal` resolves to the LXC's own IP (SSH,
raw ports). Why it's split this way is in
[Architecture](../architecture.md#how-requests-flow-at-runtime).

A typical web service gets **both**: a `*.example.com` rewrite to Caddy
plus a Caddy `reverse_proxy` block, and optionally a
`*.example.internal` rewrite straight to the LXC.

## 1. Add or edit an AdGuard rewrite

AdGuard Home runs on **LXC 117 @ `10.0.1.16`**. The rewrite playbook
derives `<service>.example.internal` from Terraform and web hostnames
from the Caddyfile. Add or update those source files first, then reconcile
AdGuard through its API from the `ansible/` directory:

```bash
cd ansible
ansible-playbook playbooks/adguard-rewrites.yml
```

The playbook uses `vault_adguard_password`; you can pass
`-e adguard_password=<pass>` instead. It leaves rewrites outside its derived
set untouched. Verify resolution from a host that uses AdGuard for DNS:

```bash
dig +short myservice.example.com
```

## 2. Add a Caddy reverse-proxy route

Caddy runs on **LXC 111 @ `10.0.1.10`** and is configured by
[`services/core/caddy/Caddyfile`](https://github.com/IanCou/Hyades/blob/main/services/core/caddy/Caddyfile).
Each web service is a site block that reverse-proxies to the backend's
`ip:port`.

1. Add a site block to the Caddyfile. For a plain HTTP backend:

   ```caddy
   myservice.example.com {
       reverse_proxy 10.0.1.42:8080
   }
   ```

   For an HTTPS backend with a self-signed cert (like the Proxmox UI), skip
   upstream verification:

   ```caddy
   myservice.example.com {
       reverse_proxy https://10.0.1.42:8443 {
           transport http {
               tls_insecure_skip_verify
           }
       }
   }
   ```

2. Deploy the change. The `caddy.yml` playbook syncs the whole Caddy directory
   (Caddyfile, Dockerfile, `.env`) and rebuilds the container:

   ```bash
   cd ansible
   ansible-playbook playbooks/caddy.yml
   ```

3. Run `playbooks/adguard-rewrites.yml` as in step 1 so the matching
   `myservice.example.com` rewrite points at Caddy (`10.0.1.10`).

4. Verify:

   ```bash
   curl -sI https://myservice.example.com
   ```

> If Caddy's own IP changed and the inventory was just updated, you can target
> the old IP for one run with
> `ansible-playbook playbooks/caddy.yml -e "ansible_host=OLD_IP"`.

## Don't forget

- After any topology change (new route, changed IP), run `make docs` from the
  repo root to regenerate the tables in `network.md`. CI fails if these are
  stale.
- A brand-new service is usually better handled end-to-end via the
  [new LXC runbook](./new-lxc.md) and the
  [new service runbook](./new-service.md), which include these DNS/proxy steps
  in context.

## Upstream docs

- [Caddy `reverse_proxy` directive](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Caddyfile concepts](https://caddyserver.com/docs/caddyfile/concepts)
- [AdGuard Home wiki](https://github.com/AdguardTeam/AdGuardHome/wiki)
- [AdGuard Home configuration reference](https://github.com/AdguardTeam/AdGuardHome/wiki/Configuration)
