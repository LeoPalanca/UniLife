#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${1:-radice}"
REMOTE_DIR="${2:-~/unilife-dashboard}"

ssh "$REMOTE_HOST" "mkdir -p $REMOTE_DIR"
scp dashboard/dist/index.html "$REMOTE_HOST:$REMOTE_DIR/index.html"

cat <<EOF
Dashboard deployed to $REMOTE_HOST:$REMOTE_DIR/index.html

To serve it on the VM:
  ssh $REMOTE_HOST
  cd $REMOTE_DIR
  python3 -m http.server 8088

If the port is not public, open a local tunnel:
  ssh -L 8088:localhost:8088 $REMOTE_HOST
  open http://localhost:8088
EOF
