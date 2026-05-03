#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${1:-radice}"
DOMAIN="${2:-unilife.ellep.it}"
REMOTE_ROOT="${3:-/var/www/unilife}"

ssh "$REMOTE_HOST" "sudo mkdir -p '$REMOTE_ROOT' && sudo chown -R debian:www-data '$REMOTE_ROOT'"

ssh "$REMOTE_HOST" "cat > /tmp/$DOMAIN.conf" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    root $REMOTE_ROOT;
    index index.html;

    access_log /var/log/nginx/$DOMAIN.access.log;
    error_log /var/log/nginx/$DOMAIN.error.log;

    location / {
        try_files \$uri \$uri/ =404;
    }
}
EOF

ssh "$REMOTE_HOST" "sudo mv /tmp/$DOMAIN.conf /etc/nginx/sites-available/$DOMAIN && sudo ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN && sudo nginx -t && sudo systemctl reload nginx"

cat <<EOF
Nginx configured for $DOMAIN
Root: $REMOTE_ROOT
EOF
