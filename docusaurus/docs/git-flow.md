---
sidebar_position: 30
---

<!-- markdownlint-disable MD013 MD060 -->

# Git flow & branch protection

This repo deploys live infrastructure: merging to `main` triggers the
`deploy` job in `ci.yml`. To keep `main` always-deployable, all changes flow through a
feature branch and a pull request, never direct commits. The full
how-to lives in
[`CONTRIBUTING.md`](https://github.com/IanCou/Hyades/blob/main/CONTRIBUTING.md);
this page explains the shape of the flow and why each rule exists.

## The flow

```text
        main
         │
         │  git switch -c feat/x
         ▼
   feat/x ●──● commits
         │
         │  git push -u origin feat/x
         │  gh pr create
         ▼
   ┌───────────────┐      no
   │  CI: validate │ ───────────▶  fix & push again
   └───────┬───────┘
           │ pass
           ▼
       review ✓
           │
           │  gh pr merge --squash --delete-branch
           ▼
        main ●  ── push triggers ci.yml ──▶ validate + lint + secret-scan ──▶ deploy
```

The `validate` job runs twice: as a required check on the PR (branch
protection requires `validate` and `lint`), and again on the merge commit. `lint` and `secret-scan` also run on PRs and the
merge commit. The `deploy` job needs all three to pass and runs only on pushes
to `main` with changed services or docs.

## Branch-protection settings

[`scripts/setup-branch-protection.sh`](https://github.com/IanCou/Hyades/blob/main/scripts/setup-branch-protection.sh)
applies these to `main`:

| Setting                  | Effect                                      | Why it matters                                 |
| ------------------------ | ------------------------------------------- | ---------------------------------------------- |
| Require a pull request   | No direct pushes to `main`                  | Every change is reviewable and CI-gated        |
| Require `validate` check | PR can't merge until CI is green            | `main` stays deployable; same gate as deploy   |
| Strict checks            | Branch must be up to date with `main` first | Prevents merging against stale code            |
| Require linear history   | Squash/rebase only, no merge commits        | Clean, bisectable history                      |
| Block force-pushes       | History on `main` can't be rewritten        | Protects the deployed source of truth          |
| Block deletions          | `main` can't be deleted                     | Prevents accidental loss of the default branch |

The script defaults to `CONTEXTS="validate"`. `ci.yml` also runs `lint` and
`secret-scan` jobs on every PR; pass `CONTEXTS="validate lint secret-scan"`
to require them before merging too. Deploy always depends on all three jobs.

## See also

- [`CONTRIBUTING.md`](https://github.com/IanCou/Hyades/blob/main/CONTRIBUTING.md): branch naming, commit style, command cheatsheet
- `.github/workflows/ci.yml`: the `validate`, `lint`, `secret-scan`, and `deploy` jobs
