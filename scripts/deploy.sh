#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
fi

mkdir -p data/runs data/history browser_data

# Build and start the container
docker compose up -d --build

# Configure Nginx reverse proxy (if nginx is installed)
if command -v nginx &>/dev/null; then
  NGINX_CONF="scripts/nginx-xhs.conf"
  SITES_AVAILABLE="/etc/nginx/sites-available/xhs"
  SITES_ENABLED="/etc/nginx/sites-enabled/xhs"

  if [ -f "$NGINX_CONF" ]; then
    cp "$NGINX_CONF" "$SITES_AVAILABLE"
    ln -sf "$SITES_AVAILABLE" "$SITES_ENABLED"

    # Remove default site if it exists (avoids port 80 conflict)
    if [ -f /etc/nginx/sites-enabled/default ]; then
      rm -f /etc/nginx/sites-enabled/default
    fi

    nginx -t && systemctl reload nginx
    echo "Nginx configured and reloaded."
  fi
fi

port="$(grep -E '^APP_PORT=' .env | tail -n 1 | cut -d '=' -f 2)"
port="${port:-8088}"

echo ""
echo "XHS Analyzer is running."
echo "Direct:   http://<your-ecs-public-ip>:${port}"
echo "Domain:   https://xhs.minamiovo.xyz (after Cloudflare DNS setup)"
