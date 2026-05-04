# Progress

## 2026-05-04

### Railway-Deploy hing auf Stand 01.05.

Live-Dashboard zeigte morgens noch Daten vom 1. Mai, obwohl Auto-Sync-Commits bis 11:05 Uhr auf Github waren. Ursache: Railway-Service hat **kein** Auto-Deploy bei Git-Push konfiguriert — `npx @railway/cli up --detach` muss explizit laufen. Auto-Sync (`sync.sh`) ruft das nicht auf, nur `git push`.

`last-modified`-Header der Live-URL als Diagnose-Werkzeug:
```
curl -sI https://pretty-kindness-production-9a7e.up.railway.app/dashboard.html | grep -i last-modified
```

**Manueller Fix:** `npx @railway/cli up --detach` ausgeführt. Nach ~90 s Build live, `last-modified: Mon, 04 May 2026 09:05:05 GMT`.

**Offene Frage:** Railway-Projekt mit Github-Repo verknüpfen (Settings → Source → Connect Repo) damit Auto-Deploy on push. Sonst muss `sync.sh` zusätzlich `railway up` triggern.

## 2026-05-01

### Team-Zuordnung aus Stammdaten-Sheet (Commit `f627e19`)

Im Master-Stammdaten-Sheet (`1xWwTkFQ...` Tab "2026") wurde Spalte B (E-Mail) eingefügt → Team rutschte von Spalte I auf J. Bisher hat `generate.py` die Team-Zuordnung aus dem Dashboard-Sheet gelesen, das aber nur grob "Vertrieb"/"Spanien" liefert. Die feine Aufteilung (S+G, Öffentlich, Privat-Wirtschaft, Hochschule) lebt im Stammdaten-Sheet.

`generate.py` lädt jetzt zusätzlich `1xWwTkFQ...!2026!A:J` und nutzt das Mitarbeiter→Team-Mapping in `parse_heute()`. Spanier behalten "Spanien" via Fallback auf das Dashboard-Sheet, weil sie in den Stammdaten nicht aufgeführt sind.

Damit funktionieren die Filter-Tabs (S+G / Öffentlich / Privat-Wirtschaft / Spanien / Hochschule) im Dashboard wieder.

### Branch-Hygiene

Vor dem Fix hatten lokal und Remote 28/31 divergente Auto-Sync-Commits. `dashboard.html` am HEAD war bit-identisch — Remote hatte aber zusätzlich Auth-Features (`server.py`, `manage_users.py`, `users.json`, neuer `sync.sh`). Lösung: `git reset --hard origin/master` mit Backup-Tag `backup-pre-reset`. Danach Team-Fix sauber on top.

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
