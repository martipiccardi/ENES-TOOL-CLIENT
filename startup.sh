#!/bin/bash
export DATA_DIR=/home/site/wwwroot/data
export XLSX_PATH=/home/site/wwwroot/data/SUPERDATASETCLEANED.xlsx
export VOL_A_HTML_CACHE_DIR=/home/vol_a_html_cache

# Oryx already set PYTHONPATH to antenv site-packages — no activation needed
echo "[startup] python: $(which python)"
echo "[startup] uvicorn available: $(python -c 'import uvicorn; print(uvicorn.__version__)' 2>&1)"
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
