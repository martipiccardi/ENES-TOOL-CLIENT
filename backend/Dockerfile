FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/

# Install CPU-only PyTorch first (avoids downloading ~5GB of CUDA libs)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')"

COPY app /app/app

# Bake pre-built semantic index into image (avoids 15+ min rebuild on deploy)
COPY semantic_index.npz /data/semantic_index.npz

ENV DATA_DIR=/data
ENV XLSX_PATH=/data/SUPERDATASETCLEANED.xlsx

EXPOSE 8501
CMD ["streamlit", "run", "app/ui.py", "--server.address=0.0.0.0", "--server.port=8501"]
