#!/usr/bin/env python3
"""
Holt aktuelle Daten aus Google Sheets via gws CLI
und regeneriert dashboard.html.
Wird als Cron-Job auf vertrieb-125 ausgeführt.
"""
import json
import re
import subprocess
import sys
from datetime import datetime

SPREADSHEET_ID = "1q4WPfKUBdXZ8lg7O7liOizBAzXUFC90VMa-n7rAQ8wg"
# Stammdaten-Sheet (HR/Personal). Tab "2026" Spalte A=Mitarbeiter, Spalte J=Team.
# Quelle der echten Team-Zuordnung (S+G, Öffentlich, Privat-Wirtschaft, ...) —
# Dashboard-Sheet liefert nur grobes "Vertrieb"/"Spanien".
STAMMDATEN_SPREADSHEET_ID = "1xWwTkFQIn-waqI2ceVCU738jHvPf_pFefO6UpdhNhZQ"
STAMMDATEN_RANGE = "2026!A2:J200"
DASHBOARD_FILE = "dashboard.html"

# ── SHEET FETCH ──────────────────────────────────────────────

def fetch_sheet(range_name, spreadsheet_id=SPREADSHEET_ID):
    result = subprocess.run(
        ["gws", "sheets", "spreadsheets", "values", "get",
         "--params", json.dumps({"spreadsheetId": spreadsheet_id, "range": range_name})],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"FEHLER beim Laden von {range_name}: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    raw = result.stdout
    # gws gibt ggf. "Using keyring backend: ..." vor dem JSON aus
    json_start = raw.find('{')
    data = json.loads(raw[json_start:])
    return data.get("values", [])

def fetch_team_mapping():
    """Mitarbeiter -> Team aus Stammdaten-Sheet (Tab '2026' Spalte J).

    Hinweis: Im April 2026 wurde im Stammdaten-Sheet eine neue Spalte B
    (E-Mail) eingefügt — Team rutschte von Spalte I auf J. Falls erneut
    verschoben wird, hier Index anpassen (TEAM_COL = 9).
    """
    NAME_COL, TEAM_COL = 0, 9
    rows = fetch_sheet(STAMMDATEN_RANGE, spreadsheet_id=STAMMDATEN_SPREADSHEET_ID)
    mapping = {}
    for row in rows:
        if len(row) <= TEAM_COL:
            continue
        name = (row[NAME_COL] or "").strip()
        team = (row[TEAM_COL] or "").strip()
        if name and team:
            mapping[name] = team
    return mapping

# ── PARSER ───────────────────────────────────────────────────

def p_int(s):
    try:
        return int(str(s).replace(".", "").replace(",", "").strip())
    except:
        return 0

def p_float(s):
    try:
        cleaned = str(s).replace(".", "").replace(",", ".").strip()
        cleaned = re.sub(r"[^\d.]", "", cleaned)
        return float(cleaned)
    except:
        return 0.0

def p_eur(s):
    """'112.364 €' oder '112364' → int"""
    try:
        cleaned = str(s).replace("\xa0", "").replace("€", "").replace(".", "").replace(",", "").strip()
        return int(float(cleaned)) if cleaned else 0
    except:
        return 0

def p_pct(s):
    """'96,9%' → 96.9"""
    try:
        return float(str(s).replace(",", ".").replace("%", "").strip())
    except:
        return 0.0

def p_days(s):
    """'13,2 Tage' → 13.2"""
    try:
        return float(str(s).replace(",", ".").replace("Tage", "").strip())
    except:
        return 0.0

def js_str(s):
    return s.replace('"', '\\"').replace("'", "\\'")

# ── PARSE HEUTE ───────────────────────────────────────────────

def parse_heute(rows, team_mapping=None):
    header = rows[0]
    data = []
    totals = {"anrufe": 0, "gespräche": 0, "terminV": 0, "terminS": 0,
              "terminG": 0, "vkE": 0, "vkG": 0}
    team_mapping = team_mapping or {}

    for row in rows[1:]:
        if not row or not row[0]:
            continue
        name = row[0].strip()
        # Datum-Zeile und Gesamt-Zeile überspringen
        if name.startswith("Datum:") or name.startswith("Team gesamt"):
            if name.startswith("Team gesamt") and len(row) >= 10:
                totals["anrufe"]    = p_int(row[3]) if len(row) > 3 else 0
                totals["gespräche"] = p_int(row[4]) if len(row) > 4 else 0
                totals["terminV"]   = p_int(row[5]) if len(row) > 5 else 0
                totals["terminS"]   = p_int(row[6]) if len(row) > 6 else 0
                totals["terminG"]   = p_int(row[7]) if len(row) > 7 else 0
                totals["vkE"]       = p_int(row[8]) if len(row) > 8 else 0
                totals["vkG"]       = p_int(row[9]) if len(row) > 9 else 0
            continue
        if len(row) < 4:
            continue

        # Team bevorzugt aus Stammdaten (echte Aufteilung S+G, Öffentlich, ...);
        # Dashboard-Sheet liefert nur "Vertrieb"/"Spanien" als Fallback.
        sheet_team = row[2].strip() if len(row) > 2 else ""
        team = team_mapping.get(name, sheet_team)
        anrufe = p_int(row[3]) if len(row) > 3 else 0
        gesp   = p_int(row[4]) if len(row) > 4 else 0
        tv     = p_int(row[5]) if len(row) > 5 else 0
        ts     = p_int(row[6]) if len(row) > 6 else 0
        tg     = p_int(row[7]) if len(row) > 7 else 0
        vke    = p_int(row[8]) if len(row) > 8 else 0
        vkg    = p_int(row[9]) if len(row) > 9 else 0

        data.append(f'  {{name:"{js_str(name)}",team:"{js_str(team)}",'
                    f'anrufe:{anrufe},gespräche:{gesp},'
                    f'terminV:{tv},terminS:{ts},terminG:{tg},'
                    f'vkE:{vke},vkG:{vkg}}}')

    js = "const heuteData = [\n" + ",\n".join(data) + "\n];"
    return js, totals

# ── PARSE SALES MANAGER ───────────────────────────────────────

def parse_sales_managers(rows):
    data = []
    for row in rows[1:]:
        if not row or not row[0]:
            continue
        name = row[0].strip()
        data.append(
            f'  {{name:"{js_str(name)}",'
            f'erstellt:{p_int(row[1]) if len(row)>1 else 0},'
            f'erstelltEur:{p_eur(row[2]) if len(row)>2 else 0},'
            f'gewonnen:{p_int(row[3]) if len(row)>3 else 0},'
            f'gewonnenEur:{p_eur(row[4]) if len(row)>4 else 0},'
            f'verloren:{p_int(row[5]) if len(row)>5 else 0},'
            f'verlorenEur:{p_eur(row[6]) if len(row)>6 else 0},'
            f'pipeline:{p_int(row[7]) if len(row)>7 else 0},'
            f'pipelineEur:{p_eur(row[8]) if len(row)>8 else 0},'
            f'avgDeal:{p_eur(row[9]) if len(row)>9 else 0},'
            f'convRate:{p_pct(row[10]) if len(row)>10 else 0},'
            f'timeToConv:{p_days(row[11]) if len(row)>11 else 0},'
            f'webinareGehalten:{p_int(row[12]) if len(row)>12 else 0},'
            f'webinareFuture:{p_int(row[13]) if len(row)>13 else 0},'
            f'webinareGesamt:{p_int(row[14]) if len(row)>14 else 0}}}'
        )
    return "const salesManagers = [\n" + ",\n".join(data) + "\n];"

# ── PARSE FUNNEL ──────────────────────────────────────────────

def parse_funnel(rows):
    data = []
    for row in rows[1:]:
        if not row or not row[0]:
            continue
        name = row[0].strip()
        data.append(
            f'  {{name:"{js_str(name)}",'
            f'anrufe:{p_int(row[1]) if len(row)>1 else 0},'
            f'gespräche:{p_int(row[2]) if len(row)>2 else 0},'
            f'terminV:{p_int(row[3]) if len(row)>3 else 0},'
            f'terminS:{p_int(row[4]) if len(row)>4 else 0},'
            f'pipeline:{p_eur(row[5]) if len(row)>5 else 0},'
            f'gewonnen:{p_eur(row[6]) if len(row)>6 else 0}}}'
        )
    return "const funnelData = [\n" + ",\n".join(data) + "\n];"

# ── HTML REPLACE ──────────────────────────────────────────────

def replace_js_array(html, const_name, new_js):
    """Ersetzt 'const NAME = [...];' im HTML.

    Per re.subn — sonst False-Positive-Warnung wenn neue Daten
    zufällig byte-identisch mit alten sind (Sheet-Stand unverändert).
    """
    pattern = rf'const {re.escape(const_name)} = \[.*?\];'
    result, n = re.subn(pattern, lambda _: new_js, html, flags=re.DOTALL)
    if n == 0:
        print(f"WARNUNG: {const_name} nicht im HTML gefunden!", file=sys.stderr)
    return result

def replace_kpi(html, totals, sync_date, sync_time):
    """Ersetzt KPI data-count-Werte und Sync-Datum.

    Anker ist das eindeutige kpi-label — verhindert, dass non-greedy
    Matching mehrere Cards verschluckt (siehe alter Bug: gesamter
    kpi-strip wurde als ein Match gewertet, nur erster data-count ersetzt).
    """
    kpi_replacements = [
        ("Anrufe heute",       totals["anrufe"]),
        ("Gespräche",          totals["gespräche"]),
        ("Termine vereinbart", totals["terminV"]),
        ("Termine stattgef.",  totals["terminS"]),
        ("Termine gehalten",   totals["terminG"]),
        ("VK erstellt",        totals["vkE"]),
        ("VK gewonnen",        totals["vkG"]),
    ]
    for label, val in kpi_replacements:
        pattern = (rf'(<div class="kpi-label">{re.escape(label)}</div>\s*'
                   rf'<div class="kpi-value" data-count=)"\d+"')
        new_html, n = re.subn(pattern, rf'\g<1>"{val}"', html, count=1)
        if n == 0:
            print(f"WARNUNG: KPI-Label '{label}' nicht im HTML gefunden!", file=sys.stderr)
        html = new_html

    # Datum-Badge
    html = re.sub(
        r'(<div class="header-badge">)([^<]+)(</div>)',
        lambda m: m.group(1) + sync_date + m.group(3),
        html, count=1
    )
    # Sync-Zeit-Badge
    html = re.sub(
        r'(<div class="header-badge"><span class="sync-dot"></span>Sync )[\d:]+(<)',
        rf'\g<1>{sync_time}\2',
        html
    )
    return html

# ── MAIN ──────────────────────────────────────────────────────

def main():
    now = datetime.now()
    sync_date = now.strftime("%-d. %B %Y").replace(
        "January","Januar").replace("February","Februar").replace(
        "March","März").replace("April","April").replace(
        "May","Mai").replace("June","Juni").replace(
        "July","Juli").replace("August","August").replace(
        "September","September").replace("October","Oktober").replace(
        "November","November").replace("December","Dezember")
    sync_time = now.strftime("%H:%M")

    print(f"[{sync_time}] Lade Daten aus Google Sheets...")

    heute_rows    = fetch_sheet("Dashboard heute!A1:J200")
    sm_rows       = fetch_sheet("all sales manager!A1:O30")
    funnel_rows   = fetch_sheet("Sales Funnel 2026!A1:J200")
    team_mapping  = fetch_team_mapping()

    print(f"Daten geladen ({len(team_mapping)} Mitarbeiter im Team-Mapping). "
          f"Generiere dashboard.html...")

    heute_js, totals = parse_heute(heute_rows, team_mapping)
    sm_js            = parse_sales_managers(sm_rows)
    funnel_js        = parse_funnel(funnel_rows)

    with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    html = replace_js_array(html, "heuteData",    heute_js)
    html = replace_js_array(html, "salesManagers", sm_js)
    html = replace_js_array(html, "funnelData",   funnel_js)
    html = replace_kpi(html, totals, sync_date, sync_time)

    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"dashboard.html aktualisiert (Sync: {sync_date} {sync_time})")
    print(f"KPIs: Anrufe={totals['anrufe']} Gespräche={totals['gespräche']} "
          f"TV={totals['terminV']} TS={totals['terminS']}")

if __name__ == "__main__":
    main()
