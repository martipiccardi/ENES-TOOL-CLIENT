"""Build semantic_index.npz from the current SUPERDATASETCLEANED.xlsx using HF API."""
import numpy as np
import pandas as pd
import requests
import time
import os

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")
MODEL = "paraphrase-multilingual-mpnet-base-v2"
URL = f"https://router.huggingface.co/hf-inference/models/sentence-transformers/{MODEL}/pipeline/feature-extraction"

def encode_batch(texts):
    resp = requests.post(
        URL,
        headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
        json={"inputs": texts, "options": {"wait_for_model": True}},
        timeout=120,
    )
    resp.raise_for_status()
    vecs = np.array(resp.json(), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return vecs / norms

base = os.path.dirname(os.path.abspath(__file__))
xlsx = os.path.join(base, "data", "SUPERDATASETCLEANED.xlsx")
out_path = os.path.join(base, "data", "semantic_index.npz")

df = pd.read_excel(xlsx, engine="openpyxl")
print(f"Loaded {len(df)} rows")

q_col = df["Question(s)"].fillna("").astype(str).str.strip()
a_col = df["Answer(s)"].fillna("").astype(str).str.strip()
texts = (q_col + " " + a_col).tolist()
row_ids = np.arange(len(texts), dtype=np.int64)

batch_size = 64
all_vecs = []
total_batches = (len(texts) + batch_size - 1) // batch_size

start = time.time()
for i in range(0, len(texts), batch_size):
    batch = texts[i : i + batch_size]
    batch_num = i // batch_size + 1
    for attempt in range(3):
        try:
            vecs = encode_batch(batch)
            all_vecs.append(vecs)
            break
        except Exception as e:
            print(f"  Batch {batch_num} attempt {attempt+1} error: {e}")
            time.sleep(5)
    else:
        raise RuntimeError(f"Failed batch {batch_num} after 3 attempts")
    if batch_num % 20 == 0 or batch_num == total_batches:
        elapsed = time.time() - start
        print(f"  Batch {batch_num}/{total_batches} done ({elapsed:.0f}s elapsed)")

embeddings = np.vstack(all_vecs)
print(f"Embeddings shape: {embeddings.shape}")

np.savez(out_path, row_ids=row_ids, embeddings=embeddings)
print(f"Saved: {out_path} ({os.path.getsize(out_path) / (1024*1024):.1f} MB)")
