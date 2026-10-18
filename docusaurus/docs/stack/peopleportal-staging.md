---
title: People Portal (staging)
sidebar_position: 57
---

# People Portal (staging)

A full staging environment for [People Portal](https://github.com/candiedoperation/TechOps),
the AppDev Club membership and team-management app, running on `appdev00` and
managed by [Coolify](./coolify.md). Publicly reachable, deliberately isolated
from the club's production instance.

- App: `https://app-corp.example.com`
- Identity: `https://app-auth.example.com` (its own Authentik)
- Deploy: Coolify service `peopleportal-core`, tunnel `appdev00`

Host: `module.appdev00` in [terraform/envs/prod/main.tf](https://github.com/IanCou/Hyades/blob/main/terraform/envs/prod/main.tf) · IP/LXC/route: [network.md](../network.md)

## Why it is isolated

The app writes Authentik groups and user attributes, and `validateServiceExistance`
runs on every boot. A staging instance pointed at the production Authentik would
write to it. So staging runs its own Authentik, its own Mongo, and its own
Postgres; nothing is shared with production.

## Switching branches

`scripts/pp-stage.sh` is the whole interface. Run it from a trusted machine, not
from `appdev00`.

```bash
./scripts/pp-stage.sh master                  # build a branch and deploy it
./scripts/pp-stage.sh feature/events          # any branch with an Nx workspace
./scripts/pp-stage.sh --image candiedoperation/people-portal:latest
./scripts/pp-stage.sh --status                # what is running right now
./scripts/pp-stage.sh --list                  # branches on the TechOps remote
```

A build-and-deploy round trip takes about 70 seconds.

It runs in two halves, on purpose. The Nx build happens over ssh on `appdev00`
via `/opt/pp-deploy/pp-build.sh`; the Coolify API calls happen locally. **The
Coolify token never goes on the box**, because `appdev00` is exposed to the
internet and that token controls every application on the Coolify instance, not
just this one.

Published images exist only for `master`: the TechOps deploy pipeline fires on
pushes to `master`, so no other branch ever produces one. That is why branches
are built here rather than pulled.

## Gotchas

**`force=true` is mandatory when changing the image.** Coolify resolves
`${PP_IMAGE}` into the compose when the service is _saved_, so an ordinary
redeploy reuses the cached resolution and keeps running the previous image while
the variable displays the new one. It looks exactly like a broken deploy.

**Health alone does not mean the deploy landed.** The old container keeps serving
while Coolify recreates it, so polling `/api/ats/openteams` returns 200 against
the image you were trying to replace. `pp-stage.sh` waits for the running image
to match the requested one _and_ be healthy; anything checking by hand should do
the same.

**Branches cut before the monorepo migration cannot be built.** They have no Nx
workspace, so there is nothing for `./nx run-many` to run. The builder exits with
an explicit message rather than a cryptic `./nx: not found`. Rebase onto `master`
to make an old branch stageable.

**The Nx wrapper requires bash.** `./nx` starts with `#!/bin/bash`, and Alpine
ships only BusyBox `sh`, so the build container is `node:23` (Debian) rather than
`node:23-alpine`. Failure mode is a misleading `./nx: not found`.

**`server/package-lock.json` is out of sync** with its `package.json` in TechOps;
several `googleapis` transitives are missing from the lock. `npm ci` fails
outright, so the build uses `npm install`, same as the Nx `install-deps` target.
Worth fixing upstream.

## Access

Authentik admin is `akadmin`. The password is `AK_PASS`, generated at provision
time and stored outside this repo. Staging is **fully open to the internet** with
no Cloudflare Access gate, a deliberate choice; that password is the only thing
in front of the identity provider.

## Related

- Tunnel: [`cloudflared-appdev00.yml`](https://github.com/IanCou/Hyades/blob/main/ansible/playbooks/cloudflared-appdev00.yml),
  a dedicated tunnel rather than a route on the caddy tunnel. Its header has the
  hostname map and why the names are flat (`app-auth`, `app-corp`).
- Coolify SSH key: [`authorize-coolify.yml`](https://github.com/IanCou/Hyades/blob/main/ansible/playbooks/authorize-coolify.yml),
  a dedicated key restricted to Coolify's LXC with `from=`.
