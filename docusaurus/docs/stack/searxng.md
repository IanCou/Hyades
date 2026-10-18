---
title: SearXNG
sidebar_position: 47
---

# SearXNG

Self-hosted, privacy-respecting metasearch engine that aggregates results from many
upstream engines.

Config: [services/prod/searxng/](https://github.com/IanCou/Hyades/tree/main/services/prod/searxng) · IP/LXC/route: [network.md](../network.md)

## Secret

`SEARXNG_SECRET` comes from `.env`; generate it once with `openssl rand -hex 32` and
never commit the value.

## Configuration

Engine/UI settings live in `settings.yml` inside the `/data/searxng` volume on the host,
not in the repo. Edit there, then `docker restart searxng`.

## References

- [SearXNG docs](https://docs.searxng.org)
- [SearXNG GitHub](https://github.com/searxng/searxng)
- [searxng-docker](https://github.com/searxng/searxng-docker)
