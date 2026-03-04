import hashlib
import html
import io
import re
import urllib.parse
import pandas as pd

from data_store import get_conn, ensure_table


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Question Bank - Search Tool",
)

# -----------------------------
# Global CSS (bigger + wrap)
# -----------------------------
st.markdown(
    """
    <style>
    /* Wider page */
    .block-container {
        max-width: 98%;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    /* "Excel-like" wrapped table container */
    .wrapped-table {
        border: 1px solid rgba(49,51,63,0.2);
        border-radius: 10px;
        padding: 0 0.25rem 0.25rem 0.25rem;
        max-height: 780px;
        overflow-y: scroll;
        overflow-x: auto;
    }
    .wrapped-table::-webkit-scrollbar {
        width: 10px;
    }
    .wrapped-table::-webkit-scrollbar-track {
        background: #f0f0f0;
        border-radius: 5px;
    }
    .wrapped-table::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 5px;
    }
    .wrapped-table::-webkit-scrollbar-thumb:hover {
        background: #555;
    }

    .wrapped-table table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.92rem;
        table-layout: fixed;
    }

    /* Cell styling + wrap */
    .wrapped-table th,
    .wrapped-table td {
        border-bottom: 1px solid #cccccc;
        padding: 10px 12px;
        vertical-align: top;
        text-align: left;

        white-space: pre-wrap;
        word-break: break-word;
        overflow-wrap: anywhere;
        line-height: 1.25rem;
    }

    /* Sticky header */
    .wrapped-table th {
        position: sticky;
        top: 0;
        z-index: 2;
        font-weight: 600;
        background: #f0f0f0 !important;
        border-bottom: 2px solid #999999 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* =========================
       COLUMN WIDTHS
       (Wave, Question Number, Mnemo, Question(s), Answer(s), FW start date, FW end date, action)
       ========================= */

    /* Wave */
    .wrapped-table th:nth-child(1),
    .wrapped-table td:nth-child(1) {
        width: 3%;
    }

    /* Question Number */
    .wrapped-table th:nth-child(2),
    .wrapped-table td:nth-child(2) {
        width: 4%;
    }

    /* Mnemo */
    .wrapped-table th:nth-child(3),
    .wrapped-table td:nth-child(3) {
        width: 4%;
    }

    /* Question(s) - largest */
    .wrapped-table th:nth-child(4),
    .wrapped-table td:nth-child(4) {
        width: 35%;
    }

    /* Answer(s) */
    .wrapped-table th:nth-child(5),
    .wrapped-table td:nth-child(5) {
        width: 25%;
    }

    /* FW start date */
    .wrapped-table th:nth-child(6),
    .wrapped-table td:nth-child(6) {
        width: 5%;
    }

    /* FW end date */
    .wrapped-table th:nth-child(7),
    .wrapped-table td:nth-child(7) {
        width: 5%;
    }

    /* Action column */
    .wrapped-table th:nth-child(8),
    .wrapped-table td:nth-child(8) {
        width: 10%;
        text-align: center;
    }

    /* Wave link button */
    .wave-links-container {
        display: flex;
        flex-wrap: wrap;
        gap: 16px 10px;
        padding: 4px 0;
    }
    .wave-link {
        display: inline-block;
        padding: 4px 10px;
        background: #4A90D9;
        color: #ffffff !important;
        border-radius: 5px;
        text-decoration: none;
        font-size: 0.82rem;
        white-space: nowrap;
    }
    .wave-link:hover {
        background: #357ABD;
    }

    /* "Waves with this Q" button */
    .q-waves-link {
        display: inline-block;
        padding: 4px 10px;
        margin-top: 4px;
        background: #5BA85B;
        color: #ffffff !important;
        border-radius: 5px;
        text-decoration: none;
        font-size: 0.82rem;
        white-space: nowrap;
    }
    .q-waves-link:hover {
        background: #4A904A;
    }

    /* "Show official source" button */
    .source-link {
        display: inline-block;
        padding: 4px 10px;
        margin-top: 4px;
        background: #D97B4A;
        color: #ffffff !important;
        border-radius: 5px;
        text-decoration: none;
        font-size: 0.82rem;
        white-space: nowrap;
    }
    .source-link:hover {
        background: #BD6A3E;
    }

    /* Highlighted row */
    .wrapped-table tr.hl-row td {
        background: #FDE68A !important;
        border-top: 2px solid #F59E0B !important;
        border-bottom: 2px solid #F59E0B !important;
    }

    /* Back to search link */
    .back-link {
        display: inline-block;
        margin-top: 3rem;
        padding: 8px 20px;
        background: #4A90D9;
        color: #ffffff !important;
        border-radius: 6px;
        text-decoration: none;
        font-size: 0.95rem;
        font-weight: 600;
    }
    .back-link:hover {
        background: #357ABD;
    }

    /* Hide deploy button */
    [data-testid="stAppDeployButton"] {
        display: none !important;
    }

    /* Sidebar spacing */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Helpers
# -----------------------------
@st.cache_data(show_spinner=False)
def get_distinct_values(column: str) -> list[str]:
    con = get_conn()
    try:
        ensure_table(con)
        df = con.execute(
            f'SELECT DISTINCT "{column}" AS v FROM enes WHERE "{column}" IS NOT NULL ORDER BY 1'
        ).fetchdf()
        return df["v"].astype(str).tolist()
    finally:
        con.close()


def _parse_period(text):
    text = text.strip()
    if not text:
        return None
    m = re.match(r'^(\d{1,2})/(\d{4})$', text)
    if not m:
        return None
    month, year = int(m.group(1)), int(m.group(2))
    if 1 <= month <= 12:
        return f"{year}-{month:02d}-01"
    return None


def _add_date_range(where, params, date_range):
    if not date_range:
        return
    date_from, date_to = date_range
    # Column values are strings like "Feb 2025" — parse to dates with TRY_STRPTIME
    if date_from:
        where.append("TRY_STRPTIME(CAST(\"FW start date\" AS VARCHAR), '%b %Y') >= CAST(? AS DATE)")
        params.append(date_from)
    if date_to:
        year, month = int(date_to[:4]), int(date_to[5:7])
        if month == 12:
            next_month = f"{year+1}-01-01"
        else:
            next_month = f"{year}-{month+1:02d}-01"
        where.append("TRY_STRPTIME(CAST(\"FW end date\" AS VARCHAR), '%b %Y') < CAST(? AS DATE)")
        params.append(next_month)


def run_query(filters, contains_filters, limit, offset, date_range=None):
    con = get_conn()
    try:
        ensure_table(con)

        where = []
        params = []

        for col, val in filters.items():
            if val:
                where.append(f'"{col}" = ?')
                params.append(val)

        for col, val in contains_filters.items():
            if val:
                where.append(f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?')
                params.append(f"%{val.lower()}%")

        _add_date_range(where, params, date_range)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        total = con.execute(
            f"SELECT COUNT(*) FROM enes {where_sql}",
            params
        ).fetchone()[0]

        df = con.execute(
            f"""
            SELECT *
            FROM enes
            {where_sql}
            ORDER BY CAST(regexp_extract("Wave", '(\d+\.?\d*)', 1) AS DOUBLE) DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset]
        ).fetchdf()

        return total, df
    finally:
        con.close()


def run_query_all(filters, contains_filters, date_range=None):
    con = get_conn()
    try:
        ensure_table(con)

        where = []
        params = []

        for col, val in filters.items():
            if val:
                where.append(f'"{col}" = ?')
                params.append(val)

        for col, val in contains_filters.items():
            if val:
                where.append(f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?')
                params.append(f"%{val.lower()}%")

        _add_date_range(where, params, date_range)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        df = con.execute(
            f"""SELECT * FROM enes {where_sql}
                ORDER BY CAST(regexp_extract("Wave", '(\d+\.?\d*)', 1) AS DOUBLE) DESC""",
            params
        ).fetchdf()

        return df
    finally:
        con.close()


def run_query_semantic(filters, sem_row_ids, sem_score_map, limit, offset,
                       date_range=None, text_filter=None, contains_filters=None):
    """Semantic results with column-specific filtering, ranked by similarity."""
    con = get_conn()
    try:
        ensure_table(con)

        where = []
        params = []

        for col, val in filters.items():
            if val:
                where.append(f'"{col}" = ?')
                params.append(val)

        _add_date_range(where, params, date_range)

        # When a related term is clicked, filter by THAT term in the relevant column
        if text_filter and contains_filters:
            for col in contains_filters:
                if contains_filters[col]:
                    where.append(f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?')
                    params.append(f"%{text_filter.lower()}%")
        elif text_filter:
            where.append(
                '(LOWER(CAST("Question(s)" AS VARCHAR)) LIKE ? '
                'OR LOWER(CAST("Answer(s)" AS VARCHAR)) LIKE ?)'
            )
            params.extend([f"%{text_filter.lower()}%", f"%{text_filter.lower()}%"])
        elif contains_filters:
            for col in contains_filters:
                if contains_filters[col]:
                    where.append(f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?')
                    params.append(f"%{contains_filters[col].lower()}%")

        # Limit to semantic results
        if sem_row_ids:
            id_list = ",".join(str(int(rid)) for rid in sem_row_ids)
            where.append(f"rowid IN ({id_list})")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        total = con.execute(
            f"SELECT COUNT(*) FROM enes {where_sql}", params
        ).fetchone()[0]

        df = con.execute(
            f"SELECT rowid AS _rid, * FROM enes {where_sql}", params
        ).fetchdf()

        # Sort by similarity score (highest first)
        df["_score"] = df["_rid"].map(lambda rid: sem_score_map.get(int(rid), 0.0))
        df = df.sort_values("_score", ascending=False)
        df = df.drop(columns=["_rid", "_score"])

        # Paginate
        df = df.iloc[offset:offset + limit].reset_index(drop=True)

        return total, df
    finally:
        con.close()


def run_query_all_semantic(filters, sem_row_ids, sem_score_map, date_range=None,
                           text_filter=None, contains_filters=None):
    """All rows matching semantic + column filters, for download."""
    con = get_conn()
    try:
        ensure_table(con)

        where = []
        params = []

        for col, val in filters.items():
            if val:
                where.append(f'"{col}" = ?')
                params.append(val)

        _add_date_range(where, params, date_range)

        if text_filter and contains_filters:
            for col in contains_filters:
                if contains_filters[col]:
                    where.append(f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?')
                    params.append(f"%{text_filter.lower()}%")
        elif text_filter:
            where.append(
                '(LOWER(CAST("Question(s)" AS VARCHAR)) LIKE ? '
                'OR LOWER(CAST("Answer(s)" AS VARCHAR)) LIKE ?)'
            )
            params.extend([f"%{text_filter.lower()}%", f"%{text_filter.lower()}%"])
        elif contains_filters:
            for col in contains_filters:
                if contains_filters[col]:
                    where.append(f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?')
                    params.append(f"%{contains_filters[col].lower()}%")

        if sem_row_ids:
            id_list = ",".join(str(int(rid)) for rid in sem_row_ids)
            where.append(f"rowid IN ({id_list})")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        df = con.execute(
            f"SELECT rowid AS _rid, * FROM enes {where_sql}", params
        ).fetchdf()

        df["_score"] = df["_rid"].map(lambda rid: sem_score_map.get(int(rid), 0.0))
        df = df.sort_values("_score", ascending=False)
        df = df.drop(columns=["_rid", "_score"])

        return df
    finally:
        con.close()


def get_wave_rows(wave_value: str) -> pd.DataFrame:
    con = get_conn()
    try:
        ensure_table(con)
        df = con.execute(
            'SELECT * FROM enes WHERE "Wave" = ?',
            [wave_value]
        ).fetchdf()
        return df
    finally:
        con.close()


def _wave_sort_key(name: str) -> float:
    """Extract the numeric part from a wave name for sorting (e.g. 'EB 104.2' -> 104.2)."""
    m = re.search(r'(\d+(?:\.\d+)?)', name)
    return float(m.group(1)) if m else 0.0


def get_waves_for_question(question_text: str) -> list[str]:
    """Return distinct waves where Question(s) matches exactly, highest number first."""
    con = get_conn()
    try:
        ensure_table(con)
        df = con.execute(
            'SELECT DISTINCT "Wave" FROM enes WHERE "Question(s)" = ?',
            [question_text]
        ).fetchdf()
        waves = [str(w) for w in df["Wave"].tolist() if pd.notna(w) and str(w).strip()]
        waves.sort(key=_wave_sort_key, reverse=True)
        return waves
    finally:
        con.close()


_DROP_COLUMNS = {"Source", "Survey Page Link"}


def _drop_hidden_cols(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[c for c in _DROP_COLUMNS if c in df.columns])


def _extract_source_links(df: pd.DataFrame) -> dict:
    """Build {row_hash: url} from the Survey Page Link column before it's dropped."""
    if "Survey Page Link" not in df.columns:
        return {}
    visible_cols = [c for c in df.columns if c not in _DROP_COLUMNS]
    links = {}
    for _, row in df.iterrows():
        url = _safe_str(row.get("Survey Page Link", "")).strip()
        if url and url.startswith("http"):
            rid = _row_hash(row, visible_cols)
            links[rid] = url
    return links


def _safe_str(val) -> str:
    if pd.isna(val):
        return ""
    return str(val)


def _row_hash(row, cols) -> str:
    raw = "|".join(_safe_str(row.get(c)) for c in cols)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _highlight_text(text: str, exact_terms: list, expanded_terms: list) -> str:
    if not text or (not exact_terms and not expanded_terms):
        return html.escape(text)
    escaped = html.escape(text)
    green_spans = []
    yellow_spans = []
    for term in exact_terms:
        if not term:
            continue
        et = html.escape(term)
        for m in re.finditer(re.escape(et), escaped, re.IGNORECASE):
            green_spans.append((m.start(), m.end()))
    for term in expanded_terms:
        if not term:
            continue
        et = html.escape(term)
        for m in re.finditer(r'\b' + re.escape(et) + r'\b', escaped, re.IGNORECASE):
            yellow_spans.append((m.start(), m.end()))
    if not green_spans and not yellow_spans:
        return escaped
    # Yellow takes priority: subtract yellow regions from green spans
    final_spans = [(ys, ye, "#FFFF99") for ys, ye in yellow_spans]
    for gs, ge in green_spans:
        remaining = [(gs, ge)]
        for ys, ye in yellow_spans:
            new_remaining = []
            for rs, rend in remaining:
                if ye <= rs or ys >= rend:
                    new_remaining.append((rs, rend))
                else:
                    if rs < ys:
                        new_remaining.append((rs, ys))
                    if rend > ye:
                        new_remaining.append((ye, rend))
            remaining = new_remaining
        for rs, rend in remaining:
            final_spans.append((rs, rend, "#90EE90"))
    final_spans.sort(key=lambda s: s[0])
    result = []
    last = 0
    for start, end, color in final_spans:
        if start < last:
            start = last
        if start >= end:
            continue
        result.append(escaped[last:start])
        result.append(f'<mark style="background:{color};padding:1px 2px;border-radius:2px">{escaped[start:end]}</mark>')
        last = end
    result.append(escaped[last:])
    return "".join(result)


def df_to_wrapped_html(
    df: pd.DataFrame,
    show_wave_link: bool = False,
    highlight_id: str = "",
    highlight_columns: dict = None,
    highlight_question: str = "",
    source_links: dict = None,
) -> str:
    if df.empty:
        return "<div>No results.</div>"

    cols = list(df.columns)
    rows_html = []

    th = "".join(f'<th style="color:#000000 !important;background:#f0f0f0 !important;">{html.escape(str(c))}</th>' for c in cols)
    if show_wave_link:
        th += '<th style="color:#000000 !important;background:#f0f0f0 !important;"></th>'
    rows_html.append(f"<tr>{th}</tr>")

    for _, row in df.iterrows():
        row_id = _row_hash(row, cols)
        is_highlight = (highlight_id and row_id == highlight_id) or \
                       (highlight_question and _safe_str(row.get("Question(s)", "")) == highlight_question)
        tr_class = ' class="hl-row"' if is_highlight else ""

        tds = []
        for c in cols:
            v = row.get(c, "")
            try:
                if pd.isna(v):
                    v = ""
                elif c in ("FW start date", "FW end date"):
                    v = pd.Timestamp(v).strftime("%b %Y")
            except (ValueError, TypeError):
                pass
            cell_text = str(v)
            if highlight_columns and c in highlight_columns:
                exact_t, expanded_t = highlight_columns[c]
                cell_html = _highlight_text(cell_text, exact_t, expanded_t)
            else:
                cell_html = html.escape(cell_text)
            tds.append(f'<td style="color:#000000 !important;background:#ffffff !important;">{cell_html}</td>')
        if show_wave_link:
            wave_val = row.get("Wave", "")
            q_text = _safe_str(row.get("Question(s)", ""))

            cell_parts = []
            if not (pd.isna(wave_val) or str(wave_val).strip() == ""):
                enc_wave = urllib.parse.quote_plus(str(wave_val))
                cell_parts.append(
                    f'<a class="wave-link" href="?show_wave={enc_wave}___{row_id}" target="_self">'
                    f'Show complete wave</a>'
                )
            if q_text.strip():
                enc_q = urllib.parse.quote_plus(q_text)
                cell_parts.append(
                    f'<a class="q-waves-link" href="?show_q_waves={enc_q}" target="_self">'
                    f'Waves with this Q</a>'
                )
            if source_links and row_id in source_links and source_links[row_id]:
                link_url = html.escape(source_links[row_id])
                cell_parts.append(
                    f'<a class="source-link" href="{link_url}" target="_blank" rel="noopener noreferrer">'
                    f'Show official source</a>'
                )
            tds.append(
                f'<td style="background:#ffffff !important;">'
                + '<br>'.join(cell_parts) + '</td>'
            )
        rows_html.append(f"<tr{tr_class}>" + "".join(tds) + "</tr>")

    return (
        '<style>'
        '.wrapped-table::-webkit-scrollbar{width:10px}'
        '.wrapped-table::-webkit-scrollbar-track{background:#f0f0f0;border-radius:5px}'
        '.wrapped-table::-webkit-scrollbar-thumb{background:#888;border-radius:5px}'
        '.wrapped-table::-webkit-scrollbar-thumb:hover{background:#555}'
        '.wrapped-table{scrollbar-width:auto;scrollbar-color:#888 #f0f0f0}'
        '</style>'
        '<div class="wrapped-table">'
        '<table>'
        + "".join(rows_html)
        + '</table>'
        '</div>'
    )


# -----------------------------
# UI – route between search page and wave page
# -----------------------------
show_wave_raw = st.query_params.get("show_wave", "")
show_q_waves = st.query_params.get("show_q_waves", "")
hl_q_param = st.query_params.get("hl_q", "")

if show_q_waves:
    # =============================
    # WAVES-WITH-THIS-QUESTION VIEW
    # =============================
    q_text = urllib.parse.unquote_plus(show_q_waves)

    st.markdown(
        '<a class="back-link" href="/" target="_self">Back to search</a>',
        unsafe_allow_html=True,
    )

    st.title("Waves containing this question")
    st.markdown(
        f'<div style="background:#f8f9fa;border-left:4px solid #4A90D9;'
        f'padding:12px 16px;margin:1rem 0;border-radius:4px;'
        f'font-size:0.95rem;color:#000000;">{html.escape(q_text)}</div>',
        unsafe_allow_html=True,
    )

    wave_list = get_waves_for_question(q_text)
    st.subheader(f"{len(wave_list)} wave(s)")

    if wave_list:
        enc_q = urllib.parse.quote_plus(q_text)
        links = []
        for w in wave_list:
            enc = urllib.parse.quote_plus(w)
            links.append(
                f'<a class="wave-link" href="?show_wave={enc}&hl_q={enc_q}" target="_self">'
                f'{html.escape(w)}</a>'
            )
        st.markdown(
            '<div class="wave-links-container">' + "".join(links) + '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No waves found for this question.")

elif show_wave_raw:
    # =============================
    # WAVE VIEW (opens in new tab)
    # =============================
    if "___" in show_wave_raw:
        wave_part, hl_id = show_wave_raw.rsplit("___", 1)
    else:
        wave_part, hl_id = show_wave_raw, ""
    selected_wave = urllib.parse.unquote_plus(wave_part)
    wave_df = get_wave_rows(selected_wave)

    # Resolve question highlight from hl_q param
    hl_question = ""
    if hl_q_param:
        hl_question = urllib.parse.unquote_plus(hl_q_param)

    back_href = "/"
    if hl_q_param:
        back_href = f"?show_q_waves={hl_q_param}"
    st.markdown(
        f'<a class="back-link" href="{back_href}" target="_self">'
        f'{"Back to waves list" if hl_q_param else "Back to search"}</a>',
        unsafe_allow_html=True,
    )

    st.title(f"Complete wave: {selected_wave}")
    st.subheader(f"{len(wave_df):,} questions")
    wave_src_links = _extract_source_links(wave_df)
    st.markdown(
        df_to_wrapped_html(_drop_hidden_cols(wave_df), highlight_id=hl_id, highlight_question=hl_question, source_links=wave_src_links),
        unsafe_allow_html=True,
    )

    st.divider()
    dl_csv, dl_xlsx = st.columns(2)
    with dl_csv:
        csv = wave_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"Download CSV ({len(wave_df):,} rows)",
            csv,
            file_name=f"wave_{selected_wave.replace(' ', '_')}.csv",
            mime="text/csv",
        )
    with dl_xlsx:
        buf = io.BytesIO()
        wave_df.to_excel(buf, index=False, engine="openpyxl")
        st.download_button(
            f"Download Excel ({len(wave_df):,} rows)",
            buf.getvalue(),
            file_name=f"wave_{selected_wave.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

else:
    # =============================
    # MAIN SEARCH VIEW
    # =============================
    st.title("QUESTION BANK - SEARCH TOOL")

    with st.sidebar:
        st.header("Filters")

        wave = st.selectbox("Wave", [""] + sorted(get_distinct_values("Wave"), key=_wave_sort_key, reverse=True))
        qnum = st.selectbox("Question Number", [""] + get_distinct_values("Question Number"))

        st.divider()
        st.subheader("Period")
        period_from = st.text_input("From (MM/YYYY)", value="", placeholder="e.g. 01/2020")
        period_to = st.text_input("To (MM/YYYY)", value="", placeholder="e.g. 12/2024")

        st.divider()
        st.subheader("Text Search")
        q_contains = st.text_input("Search in Questions", value="")
        a_contains = st.text_input("Search in Answers", value="")
        use_semantic = st.toggle("Semantic search (find similar terms)", value=True)

        st.divider()
        page_size = st.slider("Results per page", 25, 500, 100, step=25)

    filters = {
        "Wave": wave,
        "Question Number": qnum,
    }

    contains_filters = {}
    if q_contains.strip():
        contains_filters["Question(s)"] = q_contains.strip()
    if a_contains.strip():
        contains_filters["Answer(s)"] = a_contains.strip()

    # --- Period filter ---
    parsed_from = _parse_period(period_from)
    parsed_to = _parse_period(period_to)
    date_range = (parsed_from, parsed_to) if (parsed_from or parsed_to) else None

    # --- Semantic search ---
    highlight_columns = {}
    sem_row_ids = None
    sem_score_map = None
    sem_text_filter = None
    query_text = ""

    if "sem_filter" not in st.session_state:
        st.session_state.sem_filter = None

    has_text = q_contains.strip() or a_contains.strip()
    related_terms = []

    if use_semantic and has_text:
        from semantic_search import semantic_search, get_related_terms

        query_text = " ".join(
            filter(None, [q_contains.strip(), a_contains.strip()])
        )
        sem_row_ids, sem_score_map = semantic_search(query_text)

        # Determine which column to extract related terms from
        if q_contains.strip() and not a_contains.strip():
            _search_col = "q"
        elif a_contains.strip() and not q_contains.strip():
            _search_col = "a"
        else:
            _search_col = "both"

        if sem_row_ids:
            st.caption(f"Semantic search: {len(sem_row_ids)} related results found")

            # --- Related terms ---
            related_terms = get_related_terms(query_text, sem_row_ids, sem_score_map, search_col=_search_col)
            if related_terms:
                st.markdown("**Related terms** *(click to filter exact matches):*")
                n_cols = min(5, len(related_terms))
                for row_start in range(0, len(related_terms), n_cols):
                    cols = st.columns(n_cols)
                    for j, (term, score) in enumerate(related_terms[row_start:row_start + n_cols]):
                        with cols[j]:
                            is_active = st.session_state.sem_filter == term
                            label = f"{'>> ' if is_active else ''}{term} ({score})"
                            if st.button(label, key=f"sem_t_{row_start + j}"):
                                if is_active:
                                    st.session_state.sem_filter = None
                                else:
                                    st.session_state.sem_filter = term
                                st.session_state.page = 1
                                st.rerun()

            # Apply selected term filter
            if st.session_state.sem_filter:
                sem_text_filter = st.session_state.sem_filter
                st.info(f"Filtered by: **{sem_text_filter}**  — click the term again to clear")
    else:
        # Clear sem_filter when semantic search is off
        st.session_state.sem_filter = None

    # Highlighting
    expanded_q = []
    expanded_a = []
    if sem_text_filter:
        filter_words = [sem_text_filter.lower()]
        if q_contains.strip():
            expanded_q = filter_words
        if a_contains.strip():
            expanded_a = filter_words
        if not q_contains.strip() and not a_contains.strip():
            expanded_q = filter_words
            expanded_a = filter_words
    elif use_semantic and has_text and related_terms:
        # Highlight all related terms in yellow when showing all semantic results
        all_related = [t.lower() for t, _s in related_terms]
        if q_contains.strip():
            expanded_q = all_related
        if a_contains.strip():
            expanded_a = all_related
        if not q_contains.strip() and not a_contains.strip():
            expanded_q = all_related
            expanded_a = all_related

    q_exact = []
    a_exact = []
    if q_contains.strip():
        q_exact = [q_contains.strip().lower()]
    if a_contains.strip():
        a_exact = [a_contains.strip().lower()]

    if q_exact or expanded_q:
        highlight_columns["Question(s)"] = (q_exact, expanded_q)
    if a_exact or expanded_a:
        highlight_columns["Answer(s)"] = (a_exact, expanded_a)

    # --- Waves in period ---
    if date_range:
        con = get_conn()
        try:
            ensure_table(con)
            dr_where = []
            dr_params = []
            _add_date_range(dr_where, dr_params, date_range)
            for col, val in filters.items():
                if val:
                    dr_where.append(f'"{col}" = ?')
                    dr_params.append(val)
            dr_sql = "WHERE " + " AND ".join(dr_where) if dr_where else ""
            waves_df = con.execute(
                f'SELECT DISTINCT "Wave" FROM enes {dr_sql} ORDER BY "Wave"',
                dr_params
            ).fetchdf()
        finally:
            con.close()
        wave_list = [str(w) for w in waves_df["Wave"].tolist() if pd.notna(w) and str(w).strip()]
        wave_list.sort(key=_wave_sort_key, reverse=True)
        if wave_list:
            st.caption(f"Waves in this period ({len(wave_list)}):")
            links = []
            for w in wave_list:
                enc = urllib.parse.quote_plus(w)
                links.append(f'<a class="wave-link" href="?show_wave={enc}" target="_self">{html.escape(w)}</a>')
            st.markdown(
                '<div class="wave-links-container">' + "".join(links) + '</div>',
                unsafe_allow_html=True,
            )

    if "page" not in st.session_state:
        st.session_state.page = 1

    col_prev, col_mid, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button("⬅️ Previous") and st.session_state.page > 1:
            st.session_state.page -= 1
            st.rerun()

    with col_next:
        if st.button("Next ➡️"):
            st.session_state.page += 1
            st.rerun()

    offset = (st.session_state.page - 1) * page_size

    if use_semantic and has_text:
        total, df = run_query_semantic(
            filters, sem_row_ids or [], sem_score_map or {},
            page_size, offset, date_range,
            text_filter=sem_text_filter,
            contains_filters=contains_filters if sem_text_filter else None,
        )
    else:
        total, df = run_query(filters, contains_filters, page_size, offset, date_range)
    src_links = _extract_source_links(df)
    df = _drop_hidden_cols(df)

    st.subheader(f"Results: {total:,} | Page: {st.session_state.page}")

    st.markdown(
        df_to_wrapped_html(df, show_wave_link=True, highlight_columns=highlight_columns or None, source_links=src_links),
        unsafe_allow_html=True,
    )

    st.divider()

    if use_semantic and has_text:
        all_df = run_query_all_semantic(
            filters, sem_row_ids or [], sem_score_map or {},
            date_range, text_filter=sem_text_filter,
            contains_filters=contains_filters if sem_text_filter else None,
        )
    else:
        all_df = run_query_all(filters, contains_filters, date_range)

    dl_csv, dl_xlsx = st.columns(2)

    with dl_csv:
        csv = all_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"Download CSV ({total:,} results)",
            csv,
            file_name="question_bank_results.csv",
            mime="text/csv",
        )

    with dl_xlsx:
        buf = io.BytesIO()
        all_df.to_excel(buf, index=False, engine="openpyxl")
        st.download_button(
            f"Download Excel ({total:,} results)",
            buf.getvalue(),
            file_name="question_bank_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )