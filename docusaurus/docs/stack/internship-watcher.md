---
title: Internship Watcher
sidebar_position: 47
---

# Internship Watcher

Runs [github-watcher](https://github.com/IanCou/github-watcher) to watch internship-listing
repos (e.g. `SimplifyJobs/Summer2026-Internships`) and fan out matching new postings to
ntfy (phone) and a Discord webhook.

Deployed with `ansible-playbook playbooks/internship-watcher.yml`, not the standard
`deploy.yml`; it also syncs `config.yml` and runs `github-watcher config import` on every
deploy.

Config: [services/test/internship-watcher/](https://github.com/IanCou/Hyades/tree/main/services/test/internship-watcher) · IP/LXC/route: [network.md](../network.md)

## Config model

`config.yml` is only a **seed**: the import is an upsert keyed on channel/watch name, so
re-running is safe, but the SQLite database (in the `gw-data` volume) is the source of
truth after first import. Edit watches via the web UI/CLI and re-export
(`github-watcher config export`) if you want the file updated.

The first poll on a new watch primes its "seen" state without notifying, so there's no
cold-start spam.

## ntfy access

ntfy runs `auth-default-access: deny-all`, so the watcher needs an explicit publish grant
on its topic. On the ntfy host:

```sh
docker exec -it ntfy sh

ntfy user add --role=user watcher          # set a password at the prompt
ntfy access watcher simplify-internships write
ntfy token add watcher                     # copy the tk_... value into NTFY_TOKEN
```

To receive on your phone, grant your personal user read access and subscribe to the topic:

```sh
ntfy access <your-personal-user> simplify-internships read
```

See [`setup.md`](https://github.com/IanCou/Hyades/blob/main/services/test/internship-watcher/setup.md)
for the full walkthrough.

## Notes

- Watches filter on diffs to `**/listings.json` matching company patterns, not raw commit
  messages, so README cleanups and badge bumps don't trigger notifications.
- A fine-grained GitHub PAT raises the API limit to 5,000 req/hr.
- Discord webhooks are rate-limited to 30/min per webhook.

## References

- [ntfy docs](https://docs.ntfy.sh)
- [GitHub commits API](https://docs.github.com/en/rest/commits/commits)
- [Discord webhooks](https://discord.com/developers/docs/resources/webhook)
