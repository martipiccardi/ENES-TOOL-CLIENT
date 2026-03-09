#!/bin/bash
export DATA_DIR=/home/site/wwwroot/data
export XLSX_PATH=/home/site/wwwroot/data/SUPERDATASETCLEANED.xlsx
export VOL_A_HTML_CACHE_DIR=/home/vol_a_html_cache

# 1. Oryx-built venv (SCM_DO_BUILD_DURING_DEPLOYMENT=true creates this)
if [ -f "/antenv/bin/activate" ]; then
    echo "[startup] Using Oryx antenv at /antenv"
    source /antenv/bin/activate

# 2. Persistent venv on /home (survives redeployments, built once)
elif [ -f "/home/site/venv/bin/activate" ]; then
    echo "[startup] Using persistent venv at /home/site/venv"
    source /home/site/venv/bin/activate

# 3. First run: build a persistent venv (only happens once per container lifetime)
else
    echo "[startup] No venv found — creating /home/site/venv and installing packages..."
    python -m venv /home/site/venv
    source /home/site/venv/bin/activate
    pip install --no-cache-dir -q -r /home/site/wwwroot/requirements.txt
    echo "[startup] Done."
fi

cd /home/site/wwwroot
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
