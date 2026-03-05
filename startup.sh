#!/bin/bash
export DATA_DIR=/home/site/wwwroot/data
export XLSX_PATH=/home/site/wwwroot/data/SUPERDATASETCLEANED.xlsx
export VOL_A_HTML_CACHE_DIR=/home/vol_a_html_cache

VENV=/home/site/venv
STAMP="$VENV/.stamp"
# Bump this string whenever core requirements change
EXPECTED_STAMP="v1-core-hf"

if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$EXPECTED_STAMP" ]; then
    echo "Installing dependencies (first run or requirements changed)..."
    rm -rf "$VENV"
    python -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install --no-cache-dir pandas==2.2.2 openpyxl==3.1.5 xlrd==2.0.1 duckdb==1.0.0 pyarrow==17.0.0 fastapi==0.115.0 "uvicorn[standard]==0.30.6" numpy requests
    if [ -z "$HF_API_TOKEN" ]; then
        echo "Installing sentence-transformers (local model, may take ~7 min)..."
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
        pip install --no-cache-dir sentence-transformers
    fi
    echo "$EXPECTED_STAMP" > "$STAMP"
    echo "Dependencies installed."
else
    echo "Reusing existing venv (stamp: $EXPECTED_STAMP)."
    source "$VENV/bin/activate"
fi

cd /home/site/wwwroot
exec "$VENV/bin/uvicorn" backend.app.main:app --host 0.0.0.0 --port 8000
