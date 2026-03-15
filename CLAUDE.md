# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Activate the virtual environment first
venv\Scripts\activate

# Start the dashboard
streamlit run app.py

# Stop: Ctrl+C in the terminal
```

Python must be invoked as `py` (not `python`) on this machine — the `python` alias is not configured.

## Architecture

Two-file structure with clear separation:

- **`data.py`** — all data fetching and computation. No UI code.
- **`app.py`** — all Streamlit UI. Imports everything from `data.py`.

### Data flow

`fetch_stock_data()` → raw MultiIndex DataFrame (fields × tickers) → helper functions flatten it:

- `get_close(df)` → `DataFrame[date × ticker_label]` (e.g. columns: `PETR4`, `ITUB4`, `VALE3`)
- `get_volume(df)` → same shape as close
- `get_ohlcv(df, ticker_sa)` → `DataFrame[date × OHLCV]` for one ticker

`TICKER_LABELS` maps Yahoo Finance ticker IDs (`PETR4.SA`) to display labels (`PETR4`). Always use `df["Field"][ticker_sa]` to access MultiIndex columns — never `df[list_of_fields][ticker_sa]`.

### Caching

`fetch_stock_data()` is decorated with `@st.cache_data(ttl=3600)`. To force a re-fetch during development, use the **Clear cache** option in the Streamlit menu (≡) or press `C` while the app is focused.

## Known Issues & Workarounds

| Issue | Cause | Fix already applied |
|---|---|---|
| `database is locked` | yfinance SQLite timezone cache shared across processes | `yf.set_tz_cache_location()` per PID at module load in `data.py` |
| `YFRateLimitError` | Yahoo Finance rate limiting | Exponential backoff in `fetch_stock_data()` (10s→20s→40s→80s→160s) |
| `KeyError: NaTType` in slider | Empty DataFrame from failed download | Guard `if close_all.empty: st.stop()` in `app.py` |

## Dependencies

Managed in `requirements.txt` with pinned versions. Install inside the venv:

```bash
venv\Scripts\pip install -r requirements.txt
```

## GitHub Repository

Repository: https://github.com/iscarelli/brazilian-stock-dashboard

Git is configured with `origin` pointing to the repo above. The `gh` CLI is installed at `C:\Program Files\GitHub CLI\gh.exe` and authenticated as `iscarelli`.

### Auto-sync to GitHub

A background watcher (`sync_github.py`) detects file changes and automatically commits + pushes to GitHub.

```bash
# Start the watcher (keep it running in a separate terminal)
py sync_github.py
```

- Watches `.py`, `.txt`, and `.md` files (excludes `venv/`, `__pycache__/`, `.git/`)
- Waits 5 seconds after the last change before committing (debounce)
- Commit message format: `Auto-sync: YYYY-MM-DD HH:MM:SS`

To push manually:

```bash
git add .
git commit -m "your message"
git push
```
