#!/bin/bash
export TRANSFORMERS_CACHE=/home/hf_cache
export HF_HOME=/home/hf_cache
export DATA_DIR=/home/site/wwwroot/data
export XLSX_PATH=/home/site/wwwroot/data/SUPERDATASETCLEANED.xlsx

# Persistent virtualenv at /home (survives restarts)
VENV=/home/site/venv
if [ ! -f "$VENV/bin/activate" ]; then
    echo "Creating persistent virtualenv..."
    python -m venv "$VENV"
fi
source "$VENV/bin/activate"

# Install deps only if torch is not yet installed
if ! python -c "import torch" 2>/dev/null; then
    echo "Installing torch CPU-only..."
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
    echo "Installing remaining dependencies..."
    pip install --no-cache-dir -r /home/site/wwwroot/requirements.txt
fi

cd /home/site/wwwroot
streamlit run ui.py --server.port 8000 --server.address 0.0.0.0
