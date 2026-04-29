#!/bin/bash
# Cron-Sync: Google Sheets -> dashboard.html -> GitHub -> Railway
#
# Crontab-Eintrag (5 Min Versatz zum Zoho-Sync):
#   5,35 8-17 * * 1-5 "/home/bite/Schreibtisch/Vibe Coding/Projekte/bite-sales-dashboard/sync.sh" >> "/home/bite/Schreibtisch/Vibe Coding/Projekte/bite-sales-dashboard/logs/cron.log" 2>&1

set -euo pipefail

# PATH explizit setzen — Cron startet mit minimaler Umgebung,
# gws (Cargo) und node/npx (NVM) liegen außerhalb von /usr/bin
export PATH="/home/bite/.cargo/bin:/home/bite/.nvm/versions/node/v24.15.0/bin:/usr/local/bin:/usr/bin:/bin"

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

# Lock gegen Überlappen, falls ein Lauf >30 Min braucht
exec 9>/tmp/bite-dashboard-sync.lock
flock -n 9 || { echo "$(date '+%F %T') Vorheriger Sync läuft noch — abgebrochen."; exit 0; }

echo "=== $(date '+%Y-%m-%d %H:%M:%S') Dashboard-Sync gestartet ==="

# 1. Daten aus Sheets holen + HTML neu generieren
python3 generate.py

# 2. Git commit + push (nur wenn dashboard.html sich geändert hat)
git add dashboard.html
if git diff --cached --quiet; then
    echo "Keine Änderungen, Sync übersprungen."
    exit 0
fi
git commit -m "Auto-Sync: $(date '+%d.%m.%Y %H:%M')"
git push origin master

# 3. Railway neu deployen
npx --yes @railway/cli up --detach

echo "=== Sync abgeschlossen ==="
