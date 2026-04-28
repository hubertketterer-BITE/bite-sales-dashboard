# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file sales dashboard for BITE GmbH (`dashboard.html`), served by a minimal Python HTTP server. All data is embedded statically in the HTML — no backend, no database, no build step.

## Running locally

```bash
python server.py          # serves on http://localhost:8080
```

Or directly without the server script:

```bash
python -m http.server 8080
```

## Deploying to Railway

```bash
npx @railway/cli up --detach
```

Live URL: `https://pretty-kindness-production-9a7e.up.railway.app/dashboard.html`

Railway reads `Procfile` (`web: python server.py`) and injects `$PORT` automatically.

## Architecture

Everything lives in `dashboard.html`:

- **Data** — three embedded JS arrays at the bottom of the `<script>` block: `heuteData` (today's activity per person), `salesManagers` (YTD performance), `funnelData` (Sales Funnel 2026)
- **Charts** — Chart.js 4.4 loaded from CDN (`cdn.jsdelivr.net`), rendered into `<canvas>` elements
- **Styling** — inline `<style>` block using BITE brand design system (Nunito font from Google Fonts, primary `#3390ff → #65bde6` gradient)
- **Interactivity** — vanilla JS: sortable tables (click column headers), team filter tabs, animated KPI counters on load

## Data sources

Data originates from Google Sheets (spreadsheet ID `1q4WPfKUBdXZ8lg7O7liOizBAzXUFC90VMa-n7rAQ8wg`), fetched via `gws` CLI and embedded manually:

- Tab **"Dashboard heute"** → `heuteData` + KPI totals (Datum: 28.04.2026, Sync: 13:33)
- Tab **"all sales manager"** → `salesManagers`
- Tab **"Sales Funnel 2026"** → `funnelData`

To refresh data, run `gws sheets spreadsheets values get` for each tab and update the corresponding JS arrays.

## BITE design tokens

| Token | Value |
|---|---|
| Primary blue | `#3390ff` |
| Blue gradient | `linear-gradient(90deg, #3390ff, #65bde6)` |
| Dark blue | `#286ec5` |
| Font | Nunito (Google Fonts) |
| Numbers | JetBrains Mono |
| Background | `#f2f5f9` |
| Text | `#191919` |
