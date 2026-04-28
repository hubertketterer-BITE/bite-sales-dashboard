# Progress

## 2026-04-28

### Auto-Sync-Pipeline eingerichtet

- `sync.sh` Cron-tauglich gemacht: `set -euo pipefail`, expliziter PATH für `gws` (Cargo) und `node`/`npx` (NVM), `flock`-Lock gegen Überlappung, neuer Header (Pfad korrigiert von altem `Vibe Coding`-Eintrag).
- Crontab erweitert: `5,35 8-17 * * 1-5` → 5-Min-Versatz zum Zoho-Sync (Projekt 07).
- Git-Remote von HTTPS auf SSH umgestellt (Cron hat keinen Credential-Helper für HTTPS).
- Railway-Login einmalig ausgeführt, `pretty-kindness` verlinkt.
- `logs/`-Verzeichnis angelegt + in `.gitignore`.

### Bugs in `generate.py` gefixt

1. **KPI-Replacement-Bug**: Alte Regex `<div class="kpi-card">.*?</div>\s*</div>\s*</div>` matchte non-greedy den gesamten kpi-strip als einen Block, nur erste data-count wurde ersetzt. Symptom: KPIs wie "VK gewonnen" zeigten Initialwerte (0) statt Sheet-Stand.
   Neue Logik: Anker auf eindeutigem `<div class="kpi-label">LABEL</div>`, ein gezielter `re.subn` pro KPI.

2. **False-Positive-Warnung** in `replace_js_array`: Check `if result == html` meldete fälschlich "nicht gefunden", wenn neue Daten byte-identisch mit alten waren. Auf `re.subn` umgestellt, lambda als Replacement (verhindert Backref-Interpretation).

### Akzeptierte KPI-Limits

Zwei strukturelle Gründe, warum "VK gewonnen heute" niedriger sein kann als die echten Wins. Beide bewusst nicht gefixt:

1. **EXCLUDE_NAMES** in `07_Zoho_CRM_aufräumen/scripts/export_dashboard_heute.py` filtert Backoffice/Non-Sales-Mitarbeiter aus dem Dashboard. Deren Wins zählen nicht in "Team gesamt".
2. **Zoho `Closing_Date` ≠ Win-Datum**: Sheet-Formel filtert auf `Closing_Date=TODAY()`, aber Zoho's `Closing_Date` ist das *geplante* Datum (bei Deal-Erstellung gesetzt), nicht der tatsächliche Win-Tag.

Drei Lösungswege diskutiert (Zoho-Workflow / `Modified_Time`-Hack / Diff-Tracking-Spalte) — alle mit Trade-offs. Entscheidung: vorerst kein Fix.

Details siehe Vault `02 Projekte/Projects/17_Dashboard_sales/Progress.md`.
