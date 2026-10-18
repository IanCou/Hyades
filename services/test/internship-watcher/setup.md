# internship-watcher

Runs [github-watcher](https://github.com/IanCou/github-watcher) (image:
`ghcr.io/iancou/github-watcher:latest`), seeded with a watch that polls
`SimplifyJobs/Summer2026-Internships` and fans out to ntfy (phone) + a Discord
webhook only on Google/DeepMind postings. Web UI + REST API + CLI + MCP server
at `https://internship-watcher.example.com`.

## Provision ntfy access

The ntfy server runs with `auth-default-access: deny-all`, so the watcher needs an explicit publish grant for its topic.

On the ntfy host (where `services/core/ntfy` is deployed), exec into the container:

```sh
docker exec -it ntfy sh

# Create a publisher user (any password, only used internally)
ntfy user add --role=user watcher
# prompt: set a password

# Grant write-only access to the topic
ntfy access watcher simplify-internships write

# Mint an access token for the script
ntfy token add watcher
# copy the tk_... value
```

Put the `tk_...` value into `.env` as `NTFY_TOKEN=...`.

For your phone to *receive*, grant your existing personal user read access to the same topic:

```sh
ntfy access <your-personal-user> simplify-internships read
```

Then in the ntfy mobile app: add subscription `simplify-internships` against your `https://ntfy.example.com` server, logged in as your personal user.

## Deploy

Provisioning is two steps: terraform creates/sizes the LXC, ansible deploys the stack.

```sh
# From the repo root
cd terraform/envs/test
terraform apply -target=module.internship_watcher

cd ../../../ansible
ansible-playbook playbooks/internship-watcher.yml
ansible-playbook playbooks/caddy.yml   # picks up the internship-watcher.example.com route
```

Files land at `/opt/services/internship-watcher/` on LXC 602 (10.0.3.11). The playbook
also syncs `config.yml` and runs `github-watcher config import` on every deploy. It's an
upsert keyed on channel/watch name, so re-running is safe. The database is the source of
truth after first import; edit watches via the web UI/CLI going forward and re-export
(`github-watcher config export`) if you want to update this file.

First poll on a new watch primes its "seen" state without notifying, so no cold-start spam.
State persists in the `gw-data` Docker volume (SQLite), not a bind-mounted file.

## Notes

- 60s polling on the `dev` branch = ~60 req/hr against GitHub. The fine-grained PAT raises
  the limit to 5,000 req/hr.
- Discord webhooks are rate-limited to 30/min per webhook.
- The watch filters on diffs to `**/listings.json` matching `google`/`deepmind`, not raw
  commit messages, so unrelated commits (README cleanups, badge bumps) won't trigger it.
- Notification bodies lead with the matched job's actual apply URL (extracted from the same
  diff block as the matched company name), falling back to the GitHub commit link if no URL
  is found in that block.
