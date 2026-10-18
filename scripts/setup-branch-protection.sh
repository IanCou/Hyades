#!/usr/bin/env bash
#
# setup-branch-protection.sh: enforce the feature-branch → PR flow on `main`.
#
# Applies branch protection to the default branch so that:
#   - a pull request is required before merging,
#   - the CI `validate`, `lint`, and `Secret scan` status checks must pass,
#   - history stays linear (squash-merge only),
#   - force-pushes and branch deletion are blocked.
#
# Idempotent: it PUTs the full protection state, so re-running just reasserts it.
#
# Requirements:
#   - `jq` (used to build the JSON request body).
#   - GitHub CLI (`gh`) authenticated with the `repo` scope:
#       gh auth login            # or: gh auth refresh -s repo
#     The script uses gh's stored token; it never reads a token from argv/env,
#     so don't hardcode or pass one.
#
# Usage:
#   scripts/setup-branch-protection.sh                       # auto-detect repo + branch
#   REPO=owner/name scripts/setup-branch-protection.sh       # override repo
#   BRANCH=main scripts/setup-branch-protection.sh           # override branch
#   CONTEXTS="validate,lint,Secret scan" scripts/setup-branch-protection.sh
#
# ci.yml runs all three checks on every PR. CONTEXTS overrides the default
# `validate,lint,Secret scan` list with comma-separated check names.

set -euo pipefail

# --- Resolve config (env overrides; sensible defaults) ----------------------
REPO="${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
BRANCH="${BRANCH:-$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)}"
CONTEXTS="${CONTEXTS-validate,lint,Secret scan}"

# --- Preflight: required tools + auth ----------------------------------------
for tool in gh jq; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "error: '$tool' is required but not installed." >&2
    exit 1
  fi
done

if ! gh auth status >/dev/null 2>&1; then
  echo "error: gh is not authenticated. Run: gh auth login" >&2
  exit 1
fi

echo "Applying branch protection to ${REPO}@${BRANCH}"

# --- Build the required_status_checks.contexts JSON array -------------------
# Split comma-separated CONTEXTS, trimming whitespace and skipping empty names.
IFS=',' read -r -a raw_contexts <<< "$CONTEXTS"
contexts=()
for context in "${raw_contexts[@]}"; do
  context="${context#"${context%%[![:space:]]*}"}"
  context="${context%"${context##*[![:space:]]}"}"
  if [ -n "$context" ]; then
    contexts+=("$context")
  fi
done
echo "Required status checks: ${contexts[*]}"
contexts_json="$(jq -nc '$ARGS.positional' --args "${contexts[@]}")"

# --- Apply protection -------------------------------------------------------
# A single PUT replaces the entire protection object, which is what makes this
# idempotent. `--input -` feeds the JSON body on stdin.
jq -nc \
  --argjson contexts "${contexts_json}" \
  '{
    required_status_checks: {
      strict: true,
      contexts: $contexts
    },
    enforce_admins: true,
    required_pull_request_reviews: {
      required_approving_review_count: 0,
      dismiss_stale_reviews: true
    },
    restrictions: null,
    required_linear_history: true,
    allow_force_pushes: false,
    allow_deletions: false
  }' \
| gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    "repos/${REPO}/branches/${BRANCH}/protection" \
    --input - \
    >/dev/null

echo "Done. Protection is active on ${REPO}@${BRANCH}."
echo "Verify: gh api repos/${REPO}/branches/${BRANCH}/protection"
