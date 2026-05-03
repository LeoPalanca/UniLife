#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${1:-radice}"
REMOTE_DIR="${2:-/var/www/unilife}"

ssh "$REMOTE_HOST" "mkdir -p $REMOTE_DIR"
scp dashboard/dist/index.html "$REMOTE_HOST:$REMOTE_DIR/index.html"

cat <<EOF
Dashboard deployed to $REMOTE_HOST:$REMOTE_DIR/index.html
Website: http://unilife.ellep.it

If DNS is not active yet, test through the server IP with:
  curl -H 'Host: unilife.ellep.it' http://<server-ip>/
EOF
