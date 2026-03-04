import re
import hashlib
import pandas as pd

from data_store import get_conn, ensure_table

_DROP_COLUMNS = {"Source", "Survey Page Link"}


def _safe_str(val) -> str:
    if pd.isna(val):
        return ""
    return str(val)


def _row_hash(row, cols) -> str:
    raw = "|".join(_safe_str(row.get(c)) for c in cols)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _wave_sort_key(name: str) -> float:
    m = re.search(r'(\d+(?:\.\d+)?)', name)
    return float(m.group(1)) if m else 0.0


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


def get_distinct_values(column: str) -> list:
    con = get_conn()
    try:
        ensure_table(con)
        df = con.execute(
            f'SELECT DISTINCT "{column}" AS v FROM enes WHERE "{column}" IS NOT NULL ORDER BY 1'
        ).fetchdf()
        return df["v"].astype(str).tolist()
    finally:
        con.close()


def _add_must_contain_any_filter(where, params, terms, search_scope):
    """Row must contain at least one of `terms` (phrase OR any related term)."""
    if not terms:
        return
    clauses = []
    for t in terms:
        t_lower = f"%{t.lower()}%"
        if search_scope == "q":
            clauses.append('LOWER(CAST("Question(s)" AS VARCHAR)) LIKE ?')
            params.append(t_lower)
        elif search_scope == "a":
            clauses.append('LOWER(CAST("Answer(s)" AS VARCHAR)) LIKE ?')
            params.append(t_lower)
        else:
            clauses.append(
                '(LOWER(CAST("Question(s)" AS VARCHAR)) LIKE ?'
                ' OR LOWER(CAST("Answer(s)" AS VARCHAR)) LIKE ?)'
            )
            params.extend([t_lower, t_lower])
    where.append('(' + ' OR '.join(clauses) + ')')


def _add_text_filter(where, params, text_contains, search_scope):
    if not text_contains:
        return
    t = f"%{text_contains.lower()}%"
    if search_scope == "q":
        where.append('LOWER(CAST("Question(s)" AS VARCHAR)) LIKE ?')
        params.append(t)
    elif search_scope == "a":
        where.append('LOWER(CAST("Answer(s)" AS VARCHAR)) LIKE ?')
        params.append(t)
    else:
        where.append(
            '(LOWER(CAST("Question(s)" AS VARCHAR)) LIKE ? '
            'OR LOWER(CAST("Answer(s)" AS VARCHAR)) LIKE ?)'
        )
        params.extend([t, t])


def run_query(filters, text_contains, search_scope, limit, offset, date_range=None):
    con = get_conn()
    try:
        ensure_table(con)
        where = []
        params = []
        for col, val in filters.items():
            if val:
                where.append(f'"{col}" = ?')
                params.append(val)
        _add_text_filter(where, params, text_contains, search_scope)
        _add_date_range(where, params, date_range)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        total = con.execute(f"SELECT COUNT(*) FROM enes {where_sql}", params).fetchone()[0]
        df = con.execute(
            f"""SELECT * FROM enes {where_sql}
                ORDER BY CAST(regexp_extract("Wave", '(\\d+\\.?\\d*)', 1) AS DOUBLE) DESC,
                         "Question Number" ASC
                LIMIT ? OFFSET ?""",
            params + [limit, offset]
        ).fetchdf()
        return total, df
    finally:
        con.close()


def run_query_all(filters, text_contains, search_scope, date_range=None):
    con = get_conn()
    try:
        ensure_table(con)
        where = []
        params = []
        for col, val in filters.items():
            if val:
                where.append(f'"{col}" = ?')
                params.append(val)
        _add_text_filter(where, params, text_contains, search_scope)
        _add_date_range(where, params, date_range)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        df = con.execute(
            f"""SELECT * FROM enes {where_sql}
                ORDER BY CAST(regexp_extract("Wave", '(\\d+\\.?\\d*)', 1) AS DOUBLE) DESC,
                         "Question Number" ASC""",
            params
        ).fetchdf()
        return df
    finally:
        con.close()


def _add_sem_rowid_filter(where, params, sem_row_ids, must_contain_terms, search_scope):
    """Add rowid IN (sem_row_ids) OR any-related-term-match so that questions
    containing any of the must_contain_terms are never dropped even if their
    semantic similarity score falls below the threshold."""
    if not sem_row_ids:
        return
    id_list = ",".join(str(int(rid)) for rid in sem_row_ids)
    if must_contain_terms:
        # Build OR clauses for ALL related terms (not just the raw search term),
        # so any row that passes _add_must_contain_any_filter also passes here.
        term_clauses = []
        for term in must_contain_terms:
            t = f"%{term.lower()}%"
            if search_scope == "q":
                term_clauses.append('LOWER(CAST("Question(s)" AS VARCHAR)) LIKE ?')
                params.append(t)
            elif search_scope == "a":
                term_clauses.append('LOWER(CAST("Answer(s)" AS VARCHAR)) LIKE ?')
                params.append(t)
            else:
                term_clauses.append(
                    '(LOWER(CAST("Question(s)" AS VARCHAR)) LIKE ?'
                    ' OR LOWER(CAST("Answer(s)" AS VARCHAR)) LIKE ?)'
                )
                params.extend([t, t])
        where.append(f'(rowid IN ({id_list}) OR ' + ' OR '.join(term_clauses) + ')')
    else:
        where.append(f"rowid IN ({id_list})")


def run_query_semantic(filters, sem_row_ids, sem_score_map, limit, offset,
                       date_range=None, text_filter=None, text_contains=None, search_scope="both",
                       must_contain_terms=None):
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
        _add_text_filter(where, params, text_filter, search_scope)
        _add_text_filter(where, params, text_contains, search_scope)
        _add_must_contain_any_filter(where, params, must_contain_terms, search_scope)
        _add_sem_rowid_filter(where, params, sem_row_ids, must_contain_terms, search_scope)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        total = con.execute(f"SELECT COUNT(*) FROM enes {where_sql}", params).fetchone()[0]
        df = con.execute(f"SELECT rowid AS _rid, * FROM enes {where_sql}", params).fetchdf()
        df["_wave_num"] = df["Wave"].apply(lambda w: _wave_sort_key(str(w)) if pd.notna(w) else 0.0)
        df = df.sort_values(["_wave_num", "Question Number"], ascending=[False, True])
        df = df.drop(columns=["_rid", "_wave_num"])
        df = df.iloc[offset:offset + limit].reset_index(drop=True)
        return total, df
    finally:
        con.close()


def run_query_all_semantic(filters, sem_row_ids, sem_score_map, date_range=None,
                           text_filter=None, text_contains=None, search_scope="both",
                           must_contain_terms=None):
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
        _add_text_filter(where, params, text_filter, search_scope)
        _add_text_filter(where, params, text_contains, search_scope)
        _add_must_contain_any_filter(where, params, must_contain_terms, search_scope)
        _add_sem_rowid_filter(where, params, sem_row_ids, must_contain_terms, search_scope)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        df = con.execute(f"SELECT rowid AS _rid, * FROM enes {where_sql}", params).fetchdf()
        df["_wave_num"] = df["Wave"].apply(lambda w: _wave_sort_key(str(w)) if pd.notna(w) else 0.0)
        df = df.sort_values(["_wave_num", "Question Number"], ascending=[False, True])
        df = df.drop(columns=["_rid", "_wave_num"])
        return df
    finally:
        con.close()


def get_wave_rows(wave_value: str) -> pd.DataFrame:
    con = get_conn()
    try:
        ensure_table(con)
        df = con.execute('SELECT * FROM enes WHERE "Wave" = ?', [wave_value]).fetchdf()
        return df
    finally:
        con.close()


def get_waves_for_question(question_text: str, mnemo: str = '') -> list:
    con = get_conn()
    try:
        ensure_table(con)
        waves = set()

        # 1. Match by Mnemo (passed directly from the row — most reliable)
        if mnemo and mnemo.strip():
            df = con.execute(
                'SELECT DISTINCT "Wave" FROM enes WHERE "Mnemo" = ?',
                [mnemo.strip()]
            ).fetchdf()
            for w in df["Wave"].tolist():
                if pd.notna(w) and str(w).strip():
                    waves.add(str(w))

        # 2. Match by text before the first '?' (SQL-side normalization — fast)
        def _prefix(text):
            t = re.sub(r'\s+', ' ', text).strip().lower()
            idx = t.find('?')
            return t[:idx] if idx >= 0 else t

        input_prefix = _prefix(question_text)
        if input_prefix:
            sql = (
                'SELECT DISTINCT "Wave" FROM enes '
                'WHERE "Question(s)" IS NOT NULL '
                'AND LOWER(TRIM(regexp_replace('
                '  split_part(CAST("Question(s)" AS VARCHAR), \'?\', 1),'
                '  \'\\s+\', \' \', \'g\''
                '))) = ?'
            )
            df2 = con.execute(sql, [input_prefix]).fetchdf()
            for w in df2["Wave"].tolist():
                if pd.notna(w) and str(w).strip():
                    waves.add(str(w))

        result = sorted(waves, key=_wave_sort_key, reverse=True)
        return result
    finally:
        con.close()


def get_waves_in_period(date_range, filters=None) -> list:
    con = get_conn()
    try:
        ensure_table(con)
        where = []
        params = []
        _add_date_range(where, params, date_range)
        if filters:
            for col, val in filters.items():
                if val:
                    where.append(f'"{col}" = ?')
                    params.append(val)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        df = con.execute(
            f'SELECT DISTINCT "Wave" FROM enes {where_sql} ORDER BY "Wave"', params
        ).fetchdf()
        waves = [str(w) for w in df["Wave"].tolist() if pd.notna(w) and str(w).strip()]
        waves.sort(key=_wave_sort_key, reverse=True)
        return waves
    finally:
        con.close()


def df_to_rows(df: pd.DataFrame) -> list:
    """Convert DataFrame to list of serializable row dicts with _row_hash and _source_url."""
    if df.empty:
        return []
    visible_cols = [c for c in df.columns if c not in _DROP_COLUMNS]
    rows = []
    for _, row in df.iterrows():
        row_dict = {}
        for c in visible_cols:
            v = row.get(c, "")
            try:
                if pd.isna(v):
                    v = ""
                elif c in ("FW start date", "FW end date"):
                    v = pd.Timestamp(v).strftime("%b %Y")
            except (ValueError, TypeError):
                pass
            row_dict[c] = str(v) if v != "" else ""
        row_dict["_row_hash"] = _row_hash(row, visible_cols)
        source_url = _safe_str(row.get("Survey Page Link", "")).strip()
        wave_val = _safe_str(row.get("Wave", "")).strip()
        if wave_val == "EB101.5":
            source_url = "https://europa.eu/eurobarometer/surveys/detail/3226"
        row_dict["_source_url"] = source_url if source_url.startswith("http") else None
        rows.append(row_dict)
    return rows
