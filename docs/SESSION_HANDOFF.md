# SESSION HANDOFF — Dashboard-Daten-Freshness + Refresh-Skill

**Erstellt:** 2026-05-29
**Für:** neue Session, Start im Verzeichnis `00_Projekte/17_Dashboard_sales`

## Auftrag der nächsten Session

1. **Debuggen:** https://pretty-kindness-production-9a7e.up.railway.app/dashboard.html — „schon wieder nicht alle Daten aktuell" (wiederkehrend).
2. **Neuen Skill bauen:** stellt das Refreshen dieser Seite + Aktuell-Halten der Daten sicher (Monitoring/Selbstheilung, nicht nur Cron).

## Pipeline (so funktioniert das Dashboard)

```
Zoho CRM ──(separater Cron)──> Google Sheet 1q4WPfK… (3 Tabs)
                                        │
Stammdaten-Sheet 1xWwTkFQ… (Tab 2026) ──┤
                                        ▼
                         generate.py  (gws sheets values get → ersetzt JS-Arrays in dashboard.html)
                                        ▼
                         sync.sh  (git commit dashboard.html → push master → npx @railway/cli up --detach)
                                        ▼
                         Railway  (Procfile: web: python server.py)
```

- **Cron:** `5,35 8-17 * * 1-5` (alle 30 Min, 8–17 Uhr, Mo–Fr) → `sync.sh` → `logs/cron.log`
- **Datenquelle:** Sheet `1q4WPfKUBdXZ8lg7O7liOizBAzXUFC90VMa-n7rAQ8wg`, 3 Tabs:
  - `Dashboard heute!A1:J200` → `heuteData` + KPI-Totals (Zeile „Team gesamt")
  - `all sales manager!A1:O30` → `salesManagers`
  - `Sales Funnel 2026!A1:J200` → `funnelData`
- **Team-Mapping:** Stammdaten-Sheet `1xWwTkFQIn-waqI2ceVCU738jHvPf_pFefO6UpdhNhZQ`, Tab `2026`, Spalte J (Team), Spalte I (Bereich)
- **Railway-Token:** `.env` als `RAILWAY_TOKEN` (sync.sh sourct `.env`), vermeidet OAuth im headless Cron
- **GitHub:** `hubertketterer-BITE/bite-sales-dashboard`, Branch `master`

## Was am 2026-05-29 verifiziert wurde

- Letzter Auto-Sync **09:05 erfolgreich**: generate.py lief, dashboard.html committed (`40b9647`), push + Railway-Deploy OK.
- Log: `Stammdaten: 16 ausgetretene, 0 zukünftige übersprungen / 104 Mitarbeiter im Team-Mapping`.
- **Auffällig:** KPIs `Anrufe=131 Gespräche=28 TV=0 TS=0` → Termine vereinbart/stattgefunden = 0. Könnte legitim sein (früh am Tag) ODER Symptom: Spalten 5/6 im Tab „Dashboard heute" liefern 0.

## ⚠ ENTSCHEIDUNG NÖTIG: uncommitted Fix in generate.py

`git status` zeigt ` M generate.py` (Stand Mai 27, **nicht von dieser Session**). Diff:

```diff
-#   G Wh | H FTE | I Kundenmanagement | J Team
+#   G Wh | H FTE | I Bereich | J Team
-    8: "Kundenmanagement",
+    8: "Bereich",
```

→ Stammdaten-Spalte I wurde von „Kundenmanagement" auf „Bereich" umbenannt; `STAMMDATEN_HEADER_EXPECTED` wurde angepasst. **Läuft lokal** (Cron nutzt lokale Datei), ist aber **nicht in Git** → bei Re-Clone/Reset verloren.
**Aktion:** prüfen ob korrekt, dann committen + pushen (sonst gehört der Header-Check-Fix nicht zum deployten Stand).

## Debug-Hypothesen (gerankt)

1. **Partieller Upstream-Stale** — „nicht ALLE Daten aktuell" deutet auf EINEN der 3 Tabs / KPI-Block stale, Rest frisch. → Jeden Tab einzeln via `gws sheets values get` ziehen, Sheet-Stand mit Live-Dashboard vergleichen. Zuerst Zoho→Sheets-Cron für den stale Tab prüfen.
2. **Spaltenverschiebung erneut** (bekannter Bug, „2× passiert April+Mai") — Header in einem der Daten-Tabs verrutscht → `parse_*`-Index-Mapping greift falsche Spalte. Nur Stammdaten hat Header-Check; die 3 Daten-Tabs **nicht**.
3. **Railway serviert alten Build** — Deploy `--detach` ohne Verifikation. Prüfen: liefert die Live-URL die gleiche dashboard.html wie git HEAD? (`curl -s URL | grep header-badge` vs lokal).
4. **Browser-Cache** — Live-HTML ist frisch, Browser zeigt alt. Hard-Reload / `curl` gegenprüfen bevor Code angefasst wird.
5. **KPI-Regex greift nicht** — `replace_kpi` warnt bei nicht gefundenem Label; cron.log auf `WARNUNG:` grep’en.

**Erster Schritt:** `curl -s https://pretty-kindness-production-9a7e.up.railway.app/dashboard.html | grep -E 'header-badge|data-count'` → mit lokalem dashboard.html + Sheet-Ist-Stand vergleichen. Damit klärt sich sofort, ob das Problem upstream (Sheet), in generate.py, oder bei Railway/Cache liegt.

## Skill-Idee (Auftrag 2)

Neuer Skill „dashboard-refresh-guard" o.ä. — soll mehr als der reine Cron sicherstellen:
- Daten-Freshness verifizieren (Sheet-Timestamp vs. Dashboard-Badge vs. Live-HTML)
- Selbstheilung: bei Stale → re-sync triggern, bei wiederholtem Fehler → Alert (Mail via `gws gmail +send`)
- Header-Check auf ALLE 3 Daten-Tabs ausweiten (nicht nur Stammdaten)
- Pro-Tab-„last updated" sichtbar machen, damit partieller Stale auffällt
- Vor Skill-Bau: `brainstorming`-Skill nutzen (Scope klären), dann `skill-creator`.

## Relevante Dateien

| Datei | Zweck |
|---|---|
| `dashboard.html` | Single-File-Dashboard, Daten als 3 JS-Arrays eingebettet |
| `generate.py` | Sheets → dashboard.html (Parser + Regex-Replace) |
| `sync.sh` | Cron-Pipeline: generate → git → Railway |
| `server.py` | Minimaler HTTP-Server (Railway Procfile) |
| `logs/cron.log` | Sync-Historie + Fehler |
| `.env` | `RAILWAY_TOKEN` (nicht in Git) |
| `CLAUDE.md` | Architektur + Design-Tokens |
| `docs/PROGRESS.md` | Bisheriger Projektfortschritt |
