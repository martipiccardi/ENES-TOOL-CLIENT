import os
import re
from collections import Counter

import numpy as np
import requests
import streamlit as st

MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
_HF_API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{MODEL_NAME}"

_STOPWORDS = frozenset({
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
    'it', 'its', 'you', 'your', 'we', 'our', 'they', 'their', 'he', 'she',
    'not', 'no', 'if', 'so', 'as', 'up', 'out', 'all', 'also', 'any',
    'some', 'than', 'too', 'very', 'just', 'only', 'each', 'other', 'own',
    'about', 'after', 'before', 'between', 'both', 'few', 'more', 'most',
    'much', 'many', 'such', 'into', 'over', 'there', 'here', 'then',
    'now', 'when', 'where', 'what', 'which', 'who', 'why', 'how',
    'les', 'des', 'une', 'par', 'que', 'qui', 'dans', 'sur', 'pour',
    'avec', 'est', 'sont', 'pas', 'vous', 'nous', 'der', 'die', 'das',
    'und', 'ein', 'eine', 'ist', 'sind', 'nicht', 'von', 'mit',
})
INDEX_DIR = os.environ.get("DATA_DIR", "/data")


@st.cache_resource(show_spinner="Loading semantic search model …")
def _load_model():
    """Load local model. Only called when HF_API_TOKEN is NOT set."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def _hf_api_encode(texts):
    """Call HuggingFace Inference API to get embeddings. Returns normalized np.float32 array."""
    resp = requests.post(
        _HF_API_URL,
        headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
        json={"inputs": texts, "options": {"wait_for_model": True}},
        timeout=120,
    )
    resp.raise_for_status()
    vecs = np.array(resp.json(), dtype=np.float32)
    # Normalize to match sentence-transformers normalize_embeddings=True
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return vecs / norms


def _encode_texts(texts):
    """Encode a list of texts — uses HF API if token is set, local model otherwise."""
    if HF_API_TOKEN:
        return _hf_api_encode(texts)
    model = _load_model()
    return model.encode(texts, normalize_embeddings=True, batch_size=64).astype(np.float32)


@st.cache_data(ttl=300, show_spinner=False)
def _encode_query(query_text):
    """Encode a single query string, cached for reuse across functions."""
    return _encode_texts([query_text])


@st.cache_resource(show_spinner="Building search index (one-time) …")
def _build_index(_conn_factory):
    """Build or load a pre-computed embedding matrix for every row in the DB."""
    from data_store import get_conn, ensure_table

    index_path = os.path.join(INDEX_DIR, "semantic_index.npz")

    con = get_conn()
    try:
        ensure_table(con)
        df = con.execute("""
            SELECT rowid AS rid,
                   COALESCE(CAST("Question(s)" AS VARCHAR), '') AS q,
                   COALESCE(CAST("Answer(s)" AS VARCHAR), '') AS a
            FROM enes
        """).fetchdf()
    finally:
        con.close()

    row_ids = df["rid"].values.astype(np.int64)
    texts = (df["q"].str.strip() + " " + df["a"].str.strip()).tolist()
    n = len(texts)

    # Try loading cached index
    if os.path.exists(index_path):
        try:
            data = np.load(index_path)
            if data["row_ids"].shape[0] == n:
                return data["row_ids"], data["embeddings"].astype(np.float32)
        except Exception:
            pass

    if HF_API_TOKEN:
        # Batch in chunks of 64 for API
        all_vecs = []
        for i in range(0, len(texts), 64):
            all_vecs.append(_hf_api_encode(texts[i:i + 64]))
        embeddings = np.vstack(all_vecs)
    else:
        model = _load_model()
        embeddings = model.encode(
            texts,
            show_progress_bar=True,
            batch_size=128,
            normalize_embeddings=True,
        ).astype(np.float32)

    np.savez(index_path, row_ids=row_ids, embeddings=embeddings)
    return row_ids, embeddings


def semantic_search(query_text, top_n=500, threshold=0.40):
    """Return (list_of_rowids, {rowid: score}) for rows similar to *query_text*."""
    from data_store import get_conn
    row_ids, embeddings = _build_index(get_conn)

    query_vec = _encode_query(query_text)
    scores = (embeddings @ query_vec.T).flatten()

    mask = scores >= threshold
    if not mask.any():
        return [], {}

    indices = np.where(mask)[0]
    top = np.argsort(scores[indices])[::-1][:top_n]
    selected = indices[top]

    result_ids = row_ids[selected].tolist()
    score_map = {int(row_ids[i]): float(scores[i]) for i in selected}

    return result_ids, score_map


def get_related_terms(query_text, row_ids, score_map, top_n_terms=15, search_col="both"):
    """Extract related terms (1-4 words) from top semantic results, ranked by meaning closeness.

    search_col: "q" = questions only, "a" = answers only, "both" = both columns.
    """
    from data_store import get_conn, ensure_table

    # Use a wide pool of semantic results to find diverse vocabulary
    sorted_ids = sorted(row_ids, key=lambda rid: score_map.get(rid, 0), reverse=True)[:200]
    if not sorted_ids:
        return []

    con = get_conn()
    try:
        ensure_table(con)
        id_list = ",".join(str(int(rid)) for rid in sorted_ids)
        df = con.execute(f"""
            SELECT COALESCE(CAST("Question(s)" AS VARCHAR), '') AS q,
                   COALESCE(CAST("Answer(s)" AS VARCHAR), '') AS a
            FROM enes WHERE rowid IN ({id_list})
        """).fetchdf()
    finally:
        con.close()

    query_lower = query_text.lower()
    query_words = set(re.findall(r'\b\w{3,}\b', query_lower))

    ngram_counter = Counter()

    for _, row in df.iterrows():
        if search_col == "q":
            text = str(row["q"]).lower()
        elif search_col == "a":
            text = str(row["a"]).lower()
        else:
            text = (str(row["q"]) + " " + str(row["a"])).lower()
        words = re.findall(r'\b[a-zA-Z\u00C0-\u024F]{3,}\b', text)
        seen = set()
        for n in range(1, 5):
            for i in range(len(words) - n + 1):
                ngram_words = words[i:i + n]
                if all(w in _STOPWORDS for w in ngram_words):
                    continue
                if n == 1 and ngram_words[0] in _STOPWORDS:
                    continue
                # Skip any n-gram that contains a query word — those rows already appear
                if any(w in query_words for w in ngram_words):
                    continue
                ngram = " ".join(ngram_words)
                if ngram not in seen:
                    seen.add(ngram)
                    ngram_counter[ngram] += 1

    # Low frequency threshold — term just needs to appear in 2+ rows
    candidates = [(t, c) for t, c in ngram_counter.most_common(500) if c >= 2]
    if not candidates:
        return []

    # Rank by semantic similarity
    candidates = candidates[:50]
    candidate_terms = [t for t, _ in candidates]

    candidate_vecs = _encode_texts(candidate_terms)
    query_vec = _encode_query(query_text)
    sims = (candidate_vecs @ query_vec.T).flatten()

    scored = []
    for i, (term, count) in enumerate(candidates):
        sim = float(sims[i])
        if sim >= 0.25:
            scored.append((term, sim))

    scored.sort(key=lambda x: x[1], reverse=True)

    # Deduplicate: drop multi-word terms if a single-word with same/higher score covers it
    final = []
    used_singles = set()
    for term, sim in scored:
        words_in_term = term.split()
        if len(words_in_term) == 1:
            used_singles.add(term)
            final.append((term, round(sim, 2)))
        else:
            # Keep multi-word only if none of its words are already a single-word result
            if not any(w in used_singles for w in words_in_term):
                final.append((term, round(sim, 2)))
        if len(final) >= top_n_terms * 2:
            break

    # SQL verification: batch-check all candidate terms in one query
    # Fetch the text columns for ALL semantic result rows once
    con = get_conn()
    try:
        ensure_table(con)
        all_id_list = ",".join(str(int(rid)) for rid in row_ids)
        if search_col == "q":
            cols_sql = 'LOWER(CAST("Question(s)" AS VARCHAR)) AS txt'
        elif search_col == "a":
            cols_sql = 'LOWER(CAST("Answer(s)" AS VARCHAR)) AS txt'
        else:
            cols_sql = ('LOWER(CAST("Question(s)" AS VARCHAR)) || \' \' || '
                        'LOWER(CAST("Answer(s)" AS VARCHAR)) AS txt')

        all_texts = con.execute(
            f"SELECT {cols_sql} FROM enes WHERE rowid IN ({all_id_list})"
        ).fetchall()
    finally:
        con.close()

    text_blob = "\n".join(row[0] for row in all_texts if row[0])

    verified = []
    for term, sim in final:
        if term.lower() in text_blob:
            verified.append((term, sim))
        if len(verified) >= top_n_terms:
            break

    return verified


def expand_search_terms(query_text, top_n_terms=15):
    """High-level helper: run semantic search then extract related terms.

    Returns (exact_terms, expanded_terms) where:
      - exact_terms: individual words from the query (3+ chars, non-stopword)
      - expanded_terms: semantically related terms found in the corpus
    """
    exact = [w for w in re.findall(r'\b\w{3,}\b', query_text.lower())
             if w not in _STOPWORDS]

    row_ids, score_map = semantic_search(query_text)
    if not row_ids:
        return exact, []

    related = get_related_terms(query_text, row_ids, score_map,
                                top_n_terms=top_n_terms)
    expanded = [term for term, _score in related]
    return exact, expanded
