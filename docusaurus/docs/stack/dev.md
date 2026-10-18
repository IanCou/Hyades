---
title: dev
sidebar_position: 52
---

# dev

Personal dev box: Docker engine + Claude Code CLI on bare Debian, no fixed compose
stack. Used for ad hoc `docker compose` work and SSH-driven Claude Code sessions.

Provisioned with `ansible/playbooks/docker.yml -l dev` and
`ansible/playbooks/devbox.yml -l dev`. There is no `services/` directory for it;
whatever compose projects run here are managed ad hoc on the box, not via `deploy.yml`.

IP/LXC: [network.md](../network.md) · SSH: `ssh root@dev.example.internal`

## Access from a Mac

Any port a container publishes is reachable directly at `dev.example.internal:PORT`
(or the raw IP); the homelab network is flat, no reverse proxy needed for this box. For
tools that specifically require literal `localhost`, add a `LocalForward` entry to
`~/.ssh/config`.

## Claude Code browser control

`claude-in-chrome` uses Chrome's Native Messaging Host protocol: a local stdio pipe
between Chrome and a locally-spawned process, not a network socket. It cannot be bridged
over SSH. A Claude Code session running on `dev` cannot drive Chrome running on the Mac;
use a separate local Claude Code session on the Mac for anything needing browser control.
