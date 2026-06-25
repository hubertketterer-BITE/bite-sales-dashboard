# Progress

## 2026-06-25

### Live-Dashboard eingefroren — VPS-Push dauerhaft rejected (Deploy-Schicht)

**Symptom:** Railway-Live-Dashboard zeigte veraltete Werte, obwohl Master-Sheet täglich frisch (Team gesamt korrekt befüllt, `Letzter Sync` aktuell). Diagnose via Skill `sales-dashboard-doctor` → Failure Mode #2 (Deploy-Schicht), Variante "push rejected".

**Ursache (Root):** Am 23.06 wurde der Docs-Commit `18cc02c` ("docs(progress): document login reset") **lokal** in `17_Dashboard_sales` committet und auf `origin/master` gepusht — aber Schritt 3 der Deploy-Durability-Checkliste (VPS-Repo rebasen) wurde für diesen Commit übersprungen. `sync.sh` auf dem VPS hat **kein `git pull`/`rebase`** vor dem Push. Damit divergierte das VPS-Repo `/root/bite-sales-dashboard` ab 23.06 dauerhaft von origin:

1. Jeder VPS-Auto-Sync (`5,35 8-17 Mo-Fr`) generierte frisches `dashboard.html` + committete lokal.
2. `git push origin master` → `! [rejected] master -> master (fetch first)` (origin hatte `18cc02c`, das der VPS nicht hatte).
3. `set -euo pipefail` → Abbruch **vor** `railway up` → kein Deploy.
4. 40 ungepushte Auto-Sync-Commits stauten sich auf dem VPS; Live blieb auf dem letzten erfolgreichen Deploy (~23.06) eingefroren.

**Fix:** VPS-Repo auf origin rebased + gepusht (`ssh root@… 'cd /root/bite-sales-dashboard && git fetch origin && git rebase origin/master && git push origin master'`) → `18cc02c..54df4de`, 40 Commits gelandet, `0/0` synced.

**Verify (regulärer Slot, nicht nur Handlauf):** 12:05-Cron `54df4de..0d7aa54 master -> master` (Push OK) → `railway up` (Indexing/Uploading/Build-Logs-URL) → `=== Sync abgeschlossen ===`, `0/0` synced, KPIs Anrufe=562. Live deployt wieder.

**Lesson / strukturelle Wurzel:** `sync.sh` pullt nie → ein einziger Fremd-Push auf origin (z.B. lokaler Docs-/Code-Commit) friert die gesamte Deploy-Kette permanent ein, ohne Self-Heal. Empfehlung: `git pull --rebase origin master` vor dem `git push` in `sync.sh` ergänzen (Deployment-Skript → nur auf Freigabe). Bis dahin gilt die #8-Regel weiter: **jeder** lokale Push auf origin muss von einem VPS-Rebase begleitet werden — auch reine Docs-Commits.

## 2026-06-22

### Deploy-Crashloop — bcrypt-Dependency fehlte

**Symptom:** Railway-Crash-Mail Mo 22.06 06:05. Container im Restart-Loop, Deploy-Logs:
```
Traceback (most recent call last):
  File "/app/server.py", line 3, in <module>
    import bcrypt
ModuleNotFoundError: No module named 'bcrypt'
```

**Ursache:** Security-Commit `e04e4f1` stellte die Auth von hmac-Plaintext auf `bcrypt.checkpw` um (`DASHBOARD_PASSWORD` jetzt bcrypt-Hash `$2b$12$…`) und force-pushte master — aber `requirements.txt` blieb auf `# Keine externen Pakete nötig`. nixpacks installiert bcrypt nicht → Import crasht beim Start. Rollback unmöglich: ältere Deploys = hmac, können gegen den bcrypt-Hash nicht mehr authentifizieren. Nur Forward-Fix.

**Fix:** `requirements.txt` → `bcrypt>=4.0,<5` (Commit `2c54c63`).

**Deploy + Durability (3 Stellen müssen den Fix haben):**
1. `railway up --detach` aus lokalem Tree → Sofort-Fix Live
2. `git push origin master` (rebased auf laufende VPS-Auto-Syncs)
3. VPS-Repo `root@187.124.25.74:/root/bite-sales-dashboard` → `git rebase origin/master && git push` — sonst re-crasht der nächste Cron-`railway up` aus dem VPS-Tree

**Verify:** Live `/login` = HTTP 200, Deploy-Log `Server läuft auf Port 8080` ohne Traceback, `requirements.txt` auf VPS + origin enthält bcrypt.

**Lesson:** Auth-/Security-Änderungen an `server.py`, die neue Imports einführen, immer mit `requirements.txt`-Update bündeln. Der Deploy lebt an drei Stellen (Live-Container via `railway up`, origin/master, VPS-Repo) — ein Fix muss alle drei erreichen, sonst rollt der VPS-Cron ihn zurück.

### Login-Reset — DASHBOARD_PASSWORD-Hash passte nicht

**Symptom:** Nach dem Deploy-Fix kein Login möglich (`@b-ite.de` + Passwort → "E-Mail oder Passwort falsch").

**Auth-Mechanik (nicht offensichtlich):** `server.py` prüft **nicht** `users.json`. Login = beliebige `@b-ite.de`-Mail + **eine** geteilte `DASHBOARD_PASSWORD` (Railway-Env-Var = bcrypt-Hash), via `bcrypt.checkpw`. `users.json` + `manage_users.py` (pbkdf2) sind **toter Code**.

**Ursache:** Der hinterlegte Hash stammte von einem anderen Passwort (`bcrypt.checkpw` lokal gegen den Env-Hash geprüft → `NO MATCH`). bcrypt = one-way, Klartext nicht rückholbar.

**Fix:** Neuen Hash lokal via `getpass` erzeugt (Passwort nie in Chat/History), Railway-Var per **stdin** gesetzt (`railway variable set DASHBOARD_PASSWORD --stdin` — umgeht `$`-Shell-Problem mit dem `$2b$`-Hash). Var-Change triggert Redeploy. Verifiziert: neuer Hash aktiv, `/login` 200, Browser-Login geht.

**Lesson:** Passwort ändern = nur Railway-Var neu hashen, kein Code-Change. `--set "KEY=$2b$..."` zerbricht am `$` → `--stdin` nutzen. Lange Einzeiler mit `<`/`>`/`!` über das Claude-`!`-Prefix zerhacken beim Paste → in ein Script schreiben.

## 2026-05-20

### Railway-OAuth ersetzt durch Project-Token

**Symptom:** Dashboard hing seit 2026-05-19 17:35 auf altem Stand. Cron pushte HTML zu GitHub, scheiterte aber bei `railway up`:
```
Warning: failed to refresh OAuth token: Token refresh failed: invalid_grant
Unauthorized. Please run `railway login` again.
```

**Ursache:** OAuth-Refresh-Token expired. Headless Cron kann `railway login` nicht ausführen (Browser-OAuth). Erneutes interaktives `railway login` persistiert auch nicht zuverlässig — Callback-Loopback funktionierte nicht.

**Fix:**
1. Railway Project Settings (NICHT `/account/tokens`) → Tokens → New Token (Environment: production)
2. Token in `.env` als `RAILWAY_TOKEN=<uuid>` (chmod 600, gitignored)
3. `sync.sh` sourcet `.env` vor Deploy-Step:
   ```bash
   if [ -f "$REPO_DIR/.env" ]; then
       set -a
       . "$REPO_DIR/.env"
       set +a
   fi
   ```
4. CLI nimmt env-var automatisch — kein `railway login` mehr nötig

**Wichtig:** Account-Token aus `https://railway.com/account/tokens` wird vom CLI für `up` abgelehnt. Nur Project-Token funktioniert mit `RAILWAY_TOKEN`.

**Verify nach Setup:** `last-modified`-Header der Live-URL zeigt aktuelles Datum:
```
curl -sI https://pretty-kindness-production-9a7e.up.railway.app/dashboard.html | grep -i last-modified
```

Deploy-Test 09:39 → Build durch 09:42, Dashboard live mit KPIs aus 09:35-Cron (Anrufe=335 Gespräche=89 TV=4 TS=10).

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
