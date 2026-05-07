#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
fi

mkdir -p data/runs data/history browser_data

docker compose up -d --build

port="$(grep -E '^APP_PORT=' .env | tail -n 1 | cut -d '=' -f 2)"
port="${port:-8088}"

echo "XHS Analyzer is running."
echo "Open: http://<your-ecs-public-ip>:${port}"
