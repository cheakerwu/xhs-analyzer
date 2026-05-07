#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

ts="$(date +%Y%m%d-%H%M%S)"
mkdir -p backups
tar -czf "backups/xhs-analyzer-data-${ts}.tar.gz" data browser_data

echo "Backup created: backups/xhs-analyzer-data-${ts}.tar.gz"
