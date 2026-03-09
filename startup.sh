#!/bin/bash
export DATA_DIR=/home/site/wwwroot/data
export XLSX_PATH=/home/site/wwwroot/data/SUPERDATASETCLEANED.xlsx
export VOL_A_HTML_CACHE_DIR=/home/vol_a_html_cache

_verify() {
    python -c "import uvicorn, fastapi, duckdb, pandas, openpyxl" 2>/dev/null
}

_run() {
    cd /home/site/wwwroot
    exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
}

# 1. Oryx-built venv (created when SCM_DO_BUILD_DURING_DEPLOYMENT=true)
if [ -f "/antenv/bin/activate" ]; then
    source /antenv/bin/activate
    if _verify; then
        echo "[startup] /antenv OK"
        _run
    fi
    deactivate 2>/dev/null
fi

# 2. Persistent venv on /home (survives redeployments)
if [ -f "/home/site/venv/bin/activate" ]; then
    source /home/site/venv/bin/activate
    if _verify; then
        echo "[startup] /home/site/venv OK"
        _run
    fi
    echo "[startup] /home/site/venv broken — rebuilding"
    deactivate 2>/dev/null
    rm -rf /home/site/venv
fi

# 3. Build persistent venv (only when nothing else works)
echo "[startup] Installing packages into /home/site/venv..."
python -m venv /home/site/venv
source /home/site/venv/bin/activate
pip install --no-cache-dir -q -r /home/site/wwwroot/requirements.txt
echo "[startup] Done."
_run
