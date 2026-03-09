#!/bin/bash
export DATA_DIR=/home/site/wwwroot/data
export XLSX_PATH=/home/site/wwwroot/data/SUPERDATASETCLEANED.xlsx
export VOL_A_HTML_CACHE_DIR=/home/vol_a_html_cache

echo "[startup] BEGIN $(date)"
echo "[startup] /antenv exists: $([ -d /antenv ] && echo YES || echo NO)"
echo "[startup] /antenv/bin/activate: $([ -f /antenv/bin/activate ] && echo YES || echo NO)"
echo "[startup] /home/site contents: $(ls /home/site 2>&1)"

if [ -f "/antenv/bin/activate" ]; then
    source /antenv/bin/activate
    echo "[startup] /antenv activated, python: $(which python)"
else
    echo "[startup] WARNING: /antenv not found — Oryx did not run"
fi

echo "[startup] Starting uvicorn..."
cd /home/site/wwwroot
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
