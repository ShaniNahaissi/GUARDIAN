#!/usr/bin/env bash
# Local equivalent of .github/workflows/deploy.yml — run from your machine instead of CI.
set -euo pipefail
cd "$(dirname "$0")"
source ./deploy.env  # SERVER_HOST, SERVER_USER, SSH_KEY, REMOTE_PATH, [SSH_PORT, BRANCH]

BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"

ssh -i "$SSH_KEY" -o UserKnownHostsFile=./known_hosts -p "${SSH_PORT:-22}" "$SERVER_USER@$SERVER_HOST" bash -s <<EOF
  set -e
  cd "$REMOTE_PATH"
  git fetch origin "$BRANCH"
  git reset --hard "origin/$BRANCH"
  docker compose -f docker-compose.yml up --build --force-recreate -d
EOF
