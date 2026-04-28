#!/bin/bash
# Cron-Erweiterung für vertrieb-125
# Regeneriert dashboard.html aus Google Sheets und deployed zu Railway.
# Cron-Eintrag (nach dem bestehenden):
#   */30 8-17 * * 1-5 /home/bite/Schreibtisch/Vibe\ Coding/Projekte/bite-sales-dashboard/sync.sh >> /var/log/bite-dashboard.log 2>&1

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') Dashboard-Sync gestartet ==="

# 1. Daten aus Sheets holen + HTML neu generieren
python3 generate.py

# 2. Git commit + push
git add dashboard.html
git diff --cached --quiet && echo "Keine Änderungen, Sync übersprungen." && exit 0

git commit -m "Auto-Sync: $(date '+%d.%m.%Y %H:%M')"
git push origin master

# 3. Railway neu deployen
npx --yes @railway/cli up --detach

echo "=== Sync abgeschlossen ==="
