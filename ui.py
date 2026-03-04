import hashlib
import html
import io
import re
import urllib.parse
import streamlit as st
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
        padding: 0 0 0.25rem 0;
        max-height: 780px;
        overflow: auto;
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
        background: #e0e0e0 !important;
        border-bottom: 2px solid #999999 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* =========================
       COLUMN WIDTHS
       (Wave, Question Number, Mnemo, Client Number, Question(s), Answer(s), Source, FW start date, FW end date, action)
       ========================= */

    /* Wave */
    .wrapped-table th:nth-child(1),
    .wrapped-table td:nth-child(1) {
        width: 5%;
    }

    /* Question Number */
    .wrapped-table th:nth-child(2),
    .wrapped-table td:nth-child(2) {
        width: 6%;
    }

    /* Mnemo */
    .wrapped-table th:nth-child(3),
    .wrapped-table td:nth-child(3) {
        width: 4%;
    }

    /* Client Number */
    .wrapped-table th:nth-child(4),
    .wrapped-table td:nth-child(4) {
        width: 5%;
    }

    /* Question(s) - larger */
    .wrapped-table th:nth-child(5),
    .wrapped-table td:nth-child(5) {
        width: 23%;
    }

    /* Answer(s) - larger */
    .wrapped-table th:nth-child(6),
    .wrapped-table td:nth-child(6) {
        width: 21%;
    }

    /* Source */
    .wrapped-table th:nth-child(7),
    .wrapped-table td:nth-child(7) {
        width: 8%;
    }

    /* FW start date */
    .wrapped-table th:nth-child(8),
    .wrapped-table td:nth-child(8) {
        width: 7%;
    }

    /* FW end date */
    .wrapped-table th:nth-child(9),
    .wrapped-table td:nth-child(9) {
        width: 7%;
    }

    /* Action column */
    .wrapped-table th:nth-child(10),
    .wrapped-table td:nth-child(10) {
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


def run_query(filters, contains_filters, limit, offset, semantic_expansions=None, date_range=None):
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
                if semantic_expansions and col in semantic_expansions:
                    _, expanded = semantic_expansions[col]
                    or_clauses = [f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?']
                    params.append(f"%{val.lower()}%")
                    for term in expanded:
                        or_clauses.append(f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?')
                        params.append(f"%{term.lower()}%")
                    where.append("(" + " OR ".join(or_clauses) + ")")
                else:
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
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset]
        ).fetchdf()

        return total, df
    finally:
        con.close()


def run_query_all(filters, contains_filters, semantic_expansions=None, date_range=None):
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
                if semantic_expansions and col in semantic_expansions:
                    _, expanded = semantic_expansions[col]
                    or_clauses = [f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?']
                    params.append(f"%{val.lower()}%")
                    for term in expanded:
                        or_clauses.append(f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?')
                        params.append(f"%{term.lower()}%")
                    where.append("(" + " OR ".join(or_clauses) + ")")
                else:
                    where.append(f'LOWER(CAST("{col}" AS VARCHAR)) LIKE ?')
                    params.append(f"%{val.lower()}%")

        _add_date_range(where, params, date_range)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        df = con.execute(
            f"SELECT * FROM enes {where_sql}",
            params
        ).fetchdf()

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


def get_waves_for_question(question_text: str) -> list[str]:
    """Return distinct waves where Question(s) matches exactly."""
    con = get_conn()
    try:
        ensure_table(con)
        df = con.execute(
            'SELECT DISTINCT "Wave" FROM enes WHERE "Question(s)" = ? ORDER BY "Wave"',
            [question_text]
        ).fetchdf()
        return [str(w) for w in df["Wave"].tolist() if pd.notna(w) and str(w).strip()]
    finally:
        con.close()


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
    spans = []
    for term in exact_terms:
        if not term:
            continue
        et = html.escape(term)
        for m in re.finditer(re.escape(et), escaped, re.IGNORECASE):
            spans.append((m.start(), m.end(), "#90EE90"))
    for term in expanded_terms:
        if not term:
            continue
        et = html.escape(term)
        for m in re.finditer(r'\b' + re.escape(et) + r'\b', escaped, re.IGNORECASE):
            spans.append((m.start(), m.end(), "#FFFF99"))
    if not spans:
        return escaped
    spans.sort(key=lambda s: (s[0], 0 if s[2] == "#90EE90" else 1))
    merged = []
    for start, end, color in spans:
        if merged and start < merged[-1][1]:
            ps, pe, pc = merged[-1]
            if pc == "#90EE90":
                merged[-1] = (ps, max(pe, end), pc)
            else:
                merged[-1] = (ps, max(pe, end), color)
        else:
            merged.append((start, end, color))
    result = []
    last = 0
    for start, end, color in merged:
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
                q_hash = hashlib.md5(q_text.encode()).hexdigest()[:16]
                if "q_hash_map" not in st.session_state:
                    st.session_state.q_hash_map = {}
                st.session_state.q_hash_map[q_hash] = q_text
                cell_parts.append(
                    f'<a class="q-waves-link" href="?show_q_waves={q_hash}" target="_self">'
                    f'Waves with this Q</a>'
                )
            tds.append(
                f'<td style="background:#ffffff !important;">'
                + '<br>'.join(cell_parts) + '</td>'
            )
        rows_html.append(f"<tr{tr_class}>" + "".join(tds) + "</tr>")

    return (
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
    q_hash_map = st.session_state.get("q_hash_map", {})
    q_text = q_hash_map.get(show_q_waves, "")

    st.markdown(
        '<a class="back-link" href="/" target="_self">Back to search</a>',
        unsafe_allow_html=True,
    )

    if not q_text:
        st.warning("Question not found. Please go back and try again.")
    else:
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
            links = []
            for w in wave_list:
                enc = urllib.parse.quote_plus(w)
                links.append(
                    f'<a class="wave-link" href="?show_wave={enc}&hl_q={show_q_waves}" target="_self">'
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
        q_hash_map = st.session_state.get("q_hash_map", {})
        hl_question = q_hash_map.get(hl_q_param, "")

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
    st.markdown(
        df_to_wrapped_html(wave_df, highlight_id=hl_id, highlight_question=hl_question),
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

        wave = st.selectbox("Wave", [""] + get_distinct_values("Wave"))
        source = st.selectbox("Source", [""] + get_distinct_values("Source"))
        qnum = st.selectbox("Question Number", [""] + get_distinct_values("Question Number"))

        st.divider()
        st.subheader("Period")
        period_from = st.text_input("From (MM/YYYY)", value="", placeholder="e.g. 01/2020")
        period_to = st.text_input("To (MM/YYYY)", value="", placeholder="e.g. 12/2024")

        st.divider()
        st.subheader("Text Search")
        q_contains = st.text_input("Question(s) contains", value="")
        a_contains = st.text_input("Answer(s) contains", value="")
        use_semantic = st.toggle("Semantic search (find similar terms)", value=True)

        st.divider()
        page_size = st.slider("Results per page", 25, 500, 100, step=25)

        st.divider()
        view_mode = st.radio(
            "Results view",
            ["Wrapped (Excel-like) — recommended", "Grid (interactive)"],
            index=0
        )

    filters = {
        "Wave": wave,
        "Source": source,
        "Question Number": qnum,
    }

    contains_filters = {
        "Question(s)": q_contains.strip(),
        "Answer(s)": a_contains.strip(),
    }

    # --- Period filter ---
    parsed_from = _parse_period(period_from)
    parsed_to = _parse_period(period_to)
    date_range = (parsed_from, parsed_to) if (parsed_from or parsed_to) else None

    # --- Semantic expansion ---
    semantic_expansions = {}
    highlight_columns = {}

    if "sem_filter" not in st.session_state:
        st.session_state.sem_filter = None

    if use_semantic and (q_contains.strip() or a_contains.strip()):
        from semantic_search import expand_search_terms

        q_expanded = []
        a_expanded = []
        q_exact = []
        a_exact = []

        if q_contains.strip():
            q_exact, q_expanded = expand_search_terms(q_contains.strip())
        if a_contains.strip():
            a_exact, a_expanded = expand_search_terms(a_contains.strip())

        all_expanded = q_expanded + a_expanded

        # Show related terms as clickable buttons
        if all_expanded:
            st.caption("Related terms (click to filter):")
            # Show "All" button + one button per term
            btn_cols = st.columns(min(len(all_expanded) + 1, 8))
            with btn_cols[0]:
                if st.button("All", type="secondary" if st.session_state.sem_filter else "primary"):
                    st.session_state.sem_filter = None
                    st.rerun()
            for i, term in enumerate(all_expanded[:7]):
                with btn_cols[(i + 1) % min(len(all_expanded) + 1, 8)]:
                    is_active = st.session_state.sem_filter == term
                    if st.button(term, type="primary" if is_active else "secondary"):
                        st.session_state.sem_filter = term
                        st.rerun()
            # Extra row if more than 7 terms
            if len(all_expanded) > 7:
                btn_cols2 = st.columns(min(len(all_expanded) - 7, 8))
                for i, term in enumerate(all_expanded[7:15]):
                    with btn_cols2[i % min(len(all_expanded) - 7, 8)]:
                        is_active = st.session_state.sem_filter == term
                        if st.button(term, type="primary" if is_active else "secondary"):
                            st.session_state.sem_filter = term
                            st.rerun()

        # Apply filter
        active_filter = st.session_state.sem_filter
        if active_filter and active_filter in all_expanded:
            # Override search to ONLY the clicked term
            if active_filter in q_expanded and q_contains.strip():
                contains_filters["Question(s)"] = active_filter
                highlight_columns["Question(s)"] = ([active_filter], [])
            elif q_contains.strip():
                contains_filters["Question(s)"] = ""
            if active_filter in a_expanded and a_contains.strip():
                contains_filters["Answer(s)"] = active_filter
                highlight_columns["Answer(s)"] = ([active_filter], [])
            elif a_contains.strip():
                contains_filters["Answer(s)"] = ""
        else:
            if q_contains.strip():
                semantic_expansions["Question(s)"] = (q_exact, q_expanded)
                highlight_columns["Question(s)"] = ([q_contains.strip().lower()] + q_exact, q_expanded)
            if a_contains.strip():
                semantic_expansions["Answer(s)"] = (a_exact, a_expanded)
                highlight_columns["Answer(s)"] = ([a_contains.strip().lower()] + a_exact, a_expanded)
    else:
        st.session_state.sem_filter = None
        if q_contains.strip():
            q_words = [w.lower() for w in re.findall(r'\b\w{2,}\b', q_contains.strip())]
            highlight_columns["Question(s)"] = ([q_contains.strip().lower()] + q_words, [])
        if a_contains.strip():
            a_words = [w.lower() for w in re.findall(r'\b\w{2,}\b', a_contains.strip())]
            highlight_columns["Answer(s)"] = ([a_contains.strip().lower()] + a_words, [])

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

    total, df = run_query(filters, contains_filters, page_size, offset, semantic_expansions or None, date_range)

    st.subheader(f"Results: {total:,} | Page: {st.session_state.page}")

    if view_mode.startswith("Wrapped"):
        st.markdown(
            df_to_wrapped_html(df, show_wave_link=True, highlight_columns=highlight_columns or None),
            unsafe_allow_html=True,
        )
    else:
        st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=True,
            height=780
        )

    st.divider()

    all_df = run_query_all(filters, contains_filters, semantic_expansions or None, date_range)

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