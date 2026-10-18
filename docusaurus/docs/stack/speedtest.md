---
title: Speedtest Tracker
sidebar_position: 46
---

# Speedtest Tracker

Runs scheduled internet speed tests (hourly) and tracks download/upload/latency history
over time, with a web dashboard.

Config: [services/core/speedtest/](https://github.com/IanCou/Hyades/tree/main/services/core/speedtest) · IP/LXC/route: [network.md](../network.md)

## Gotcha: `APP_KEY`

`APP_KEY` is the only secret and is **required**. It must be a valid Laravel base64 key
(generate with `echo "base64:$(openssl rand -base64 32)"`) and is supplied at deploy time
from CI secrets, not committed.

## References

- [Speedtest Tracker docs](https://docs.speedtest-tracker.dev/)
- [LinuxServer.io image](https://docs.linuxserver.io/images/docker-speedtest-tracker/)
