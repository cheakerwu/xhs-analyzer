#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Configure Docker mirror for China region (skip if already configured)
DOCKER_DAEMON="/etc/docker/daemon.json"
if [ ! -f "$DOCKER_DAEMON" ] || ! grep -q "registry-mirrors" "$DOCKER_DAEMON" 2>/dev/null; then
  mkdir -p /etc/docker
  cat > "$DOCKER_DAEMON" <<'MIRROR'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
MIRROR
  systemctl daemon-reload
  systemctl restart docker
  echo "Docker mirror configured."
fi

if [ ! -f .env ]; then
  cp .env.example .env
fi

mkdir -p data/runs data/history browser_data

# Build and start the container
docker compose up -d --build

# Configure Nginx reverse proxy (if nginx is installed)
if command -v nginx &>/dev/null; then
  NGINX_CONF="scripts/nginx-xhs.conf"

  if [ -d /etc/nginx/conf.d ]; then
    # CentOS / RHEL / Alibaba Cloud Linux
    cp "$NGINX_CONF" /etc/nginx/conf.d/xhs.conf
  elif [ -d /etc/nginx/sites-available ]; then
    # Ubuntu / Debian
    cp "$NGINX_CONF" /etc/nginx/sites-available/xhs
    ln -sf /etc/nginx/sites-available/xhs /etc/nginx/sites-enabled/xhs
    [ -f /etc/nginx/sites-enabled/default ] && rm -f /etc/nginx/sites-enabled/default
  fi

  nginx -t && systemctl reload nginx
  echo "Nginx configured and reloaded."
fi

port="$(grep -E '^APP_PORT=' .env | tail -n 1 | cut -d '=' -f 2)"
port="${port:-8088}"

echo ""
echo "XHS Analyzer is running."
echo "Direct:   http://<your-ecs-public-ip>:${port}"
echo "Domain:   https://xhs.minamiovo.xyz (after Cloudflare DNS setup)"
