---
title: Update docs
sidebar_position: 5
---

# Update docs

Added 2026-04-17. See [docs-site stack](../stack/docs-site.md) for how it's wired.

## Edit locally (hot reload)

```bash
cd docusaurus
npm install   # first time only
npm start     # http://localhost:3000, reloads on save
```

- `docs/**` → appears under `/docs/`

[Docusaurus CLI](https://docusaurus.io/docs/cli).

## Deploy

Push to `main`. The self-hosted runner watches `docusaurus/**` and runs
`ansible-playbook playbooks/docs.yml` automatically.

### Manual deploy

```bash
cd ansible
ansible-playbook playbooks/docs.yml
```

Rsyncs source to LXC 118 and runs `docker compose up --build`. First build
~2 min, incremental ~30s.

## Add a new page

1. Drop a `.md` under `docusaurus/docs/`.
2. Frontmatter is optional; use it for ordering / title overrides:

   ```md
   ---
   title: My page
   sidebar_position: 3
   ---
   ```

3. To add a new category, create a folder and an optional `_category_.json`:

   ```json
   { "label": "My category", "position": 10 }
   ```

[Docusaurus docs folder structure](https://docusaurus.io/docs/docs-introduction).

## Add a new top-level section

Edit `docusaurus/docusaurus.config.js` and add a
`@docusaurus/plugin-content-docs` entry under `plugins` (with its own `id`,
`path`, `routeBasePath`, `sidebarPath`). Then add its sidebar file and a
navbar link. See
[multi-instance docs](https://docusaurus.io/docs/docs-multi-instance).

## Troubleshooting

- **MDX parse error** on a `.md` file: ensure `markdown.format: 'detect'`
  is set in `docusaurus.config.js` (so plain Markdown stays CommonMark).
- **Broken link warnings across instances**: if you add a second docs
  instance, cross-instance links must be absolute (`/docs/...`), not relative.
- **`/` shows 404**: each instance needs an `index.md` with `slug: /`.
