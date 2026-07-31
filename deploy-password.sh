#!/usr/bin/env bash
# Password-auth variant of deploy.sh, using PuTTY's plink (already installed on this machine).
set -euo pipefail
cd "$(dirname "$0")"
source ./deploy-password.env  # SERVER_HOST, SERVER_USER, SERVER_PASSWORD, REMOTE_PATH, [SSH_PORT, BRANCH]

BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
PLINK="/c/Program Files/PuTTY/plink.exe"

# Optional: pass a commit message as $1 to commit+push local changes before deploying.
if [ -n "${1:-}" ]; then
  git add -A
  git commit -m "$1"
  git push origin "$BRANCH"
fi

"$PLINK" -ssh -batch -hostkey "SHA256:7SRnay3BCGNQ1UrEy+u8qwl1OPdLZLjibHB46j4+JlA" -pw "$SERVER_PASSWORD" -P "${SSH_PORT:-22}" "$SERVER_USER@$SERVER_HOST" "
  set -e
  cd '$REMOTE_PATH'
  git fetch origin '$BRANCH'
  git reset --hard 'origin/$BRANCH'
  docker compose -f docker-compose.yml up --build --force-recreate -d
"
