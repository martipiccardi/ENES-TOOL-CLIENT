#!/bin/bash
export DATA_DIR=/home/site/wwwroot/data
export XLSX_PATH=/home/site/wwwroot/data/SUPERDATASETCLEANED.xlsx
export VOL_A_HTML_CACHE_DIR=/home/vol_a_html_cache

# Oryx builds packages into /antenv during deployment (SCM_DO_BUILD_DURING_DEPLOYMENT=true)
# If /antenv exists, activate it. Otherwise try system Python (will fail fast with import error).
if [ -f "/antenv/bin/activate" ]; then
    source /antenv/bin/activate
    echo "[startup] /antenv activated"
else
    echo "[startup] WARNING: /antenv not found — Oryx may not have run"
fi

cd /home/site/wwwroot
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
