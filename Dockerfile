FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV GENSIM_DATA_DIR=/data/gensim-data
RUN python -c "import gensim.downloader as api; api.load('glove-wiki-gigaword-50')"
COPY data_store.py .
COPY semantic_search.py .
COPY ui.py .
COPY data/ /data/
ENV DATA_DIR=/data
ENV XLSX_PATH=/data/SUPERDATASETCLEANED.xlsx
EXPOSE 8501
CMD ["streamlit", "run", "ui.py", "--server.address=0.0.0.0", "--server.port=8501"]
