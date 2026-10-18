#!/usr/bin/env bash
#
# pp-stage.sh: point the People Portal staging environment at a branch.
#
#   ./pp-stage.sh master                    build master on appdev00 and deploy it
#   ./pp-stage.sh feature/events            same, for any branch with an Nx workspace
#   ./pp-stage.sh --image candiedoperation/people-portal:latest
#                                           deploy a published image, no build
#   ./pp-stage.sh --status                  what is running right now
#   ./pp-stage.sh --list                    branches on the TechOps remote
#
# Runs from a trusted machine, not from appdev00. The build happens over ssh on
# the box; the Coolify API calls happen here, so the Coolify token never lands
# on a host that is exposed to the internet. That token controls every
# application on the Coolify instance, not just this one.
#
# Reads COOLIFY_API_TOKEN from the environment, falling back to
# ~/Documents/Env/coolify.env.
set -euo pipefail

HOST=root@appdev00
BUILDER=/opt/pp-deploy/pp-build.sh
COOLIFY=https://coolify.example.com
SVC=z823m13gxlqdqg3vjgv8vvi9
APP_CONTAINER="people-portal-${SVC}"
PUBLIC_URL=https://app-corp.example.com

# BSD sed (macOS) has no \? operator, so strip the comment prefix in two steps.
usage() { sed -n '3,10p' "$0" | sed -e 's/^# //' -e 's/^#//'; exit "${1:-1}"; }

token() {
  if [ -n "${COOLIFY_API_TOKEN:-}" ]; then printf '%s' "$COOLIFY_API_TOKEN"; return; fi
  local f="$HOME/Documents/Env/coolify.env"
  [ -f "$f" ] || { echo "COOLIFY_API_TOKEN not set and $f missing" >&2; exit 1; }
  set -a
  # shellcheck disable=SC1090
  . "$f"
  set +a
  printf '%s' "${COOLIFY_API_TOKEN:?COOLIFY_API_TOKEN missing from $f}"
}

running_image() {
  ssh -o BatchMode=yes "$HOST" \
    "docker inspect $APP_CONTAINER --format '{{.Config.Image}}' 2>/dev/null || echo '(not running)'"
}

deploy() {
  local image="$1" tok; tok=$(token)

  echo "==> pointing Coolify at $image"
  curl -sS -X PATCH -H "Authorization: Bearer $tok" -H "Content-Type: application/json" \
    -d "{\"key\":\"PP_IMAGE\",\"value\":\"$image\"}" \
    "$COOLIFY/api/v1/services/$SVC/envs" >/dev/null

  # force=true is required, not defensive: Coolify resolves ${PP_IMAGE} into the
  # compose when the service is saved, so an ordinary deploy reuses the cached
  # resolution and silently keeps running the previous image.
  echo "==> redeploying (forced)"
  curl -sS -H "Authorization: Bearer $tok" \
    "$COOLIFY/api/v1/deploy?uuid=$SVC&force=true" >/dev/null

  # Both conditions matter. Polling health alone reports success immediately,
  # because the OLD container is still up and serving while Coolify is still
  # recreating it. The image must actually be the one we asked for.
  echo "==> waiting for $image to be live and healthy"
  for _ in $(seq 1 40); do
    if [ "$(running_image)" = "$image" ] && ssh -o BatchMode=yes "$HOST" \
        'curl -sf -o /dev/null --max-time 8 http://localhost:3000/api/ats/openteams'; then
      echo "    healthy: $PUBLIC_URL"
      echo "    running: $image"
      return 0
    fi
    sleep 10
  done

  echo "    FAILED health check after ~7min; last 20 log lines:" >&2
  ssh -o BatchMode=yes "$HOST" "docker logs $APP_CONTAINER --tail 20" >&2
  exit 1
}

case "${1:-}" in
  ""|-h|--help) usage 0 ;;
  --list)       ssh -o BatchMode=yes "$HOST" "$BUILDER --list" ;;
  --status)
    echo "running: $(running_image)"
    curl -s -o /dev/null -w "public : http=%{http_code}\n" --max-time 20 "$PUBLIC_URL/"
    ;;
  --image)
    deploy "${2:?--image needs an image reference}"
    ;;
  -*)
    echo "unknown option: $1" >&2; usage
    ;;
  *)
    BRANCH="$1"
    # Mirror the builder's tag rule rather than parsing its output: docker tags
    # reject slashes, which several branches here use.
    TAG="branch-$(printf '%s' "$BRANCH" | tr '/' '-' | tr -cd '[:alnum:]._-')"
    echo "==> building $BRANCH on ${HOST#*@}"
    ssh -o BatchMode=yes "$HOST" "$BUILDER '$BRANCH'"
    deploy "people-portal:${TAG}"
    ;;
esac
