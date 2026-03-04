import os
from pathlib import Path

import duckdb
import pandas as pd

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
XLSX_PATH = Path(os.environ.get("XLSX_PATH", "./data/SUPERDATASETCLEANED.xlsx"))

DB_PATH = DATA_DIR / "enes.duckdb"


def get_conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def ensure_table(con: duckdb.DuckDBPyConnection):
    """
    Create TABLE enes once from Excel.
    This is the original, stable version.
    """
    # If table already exists, do nothing
    exists = con.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = 'enes'
    """).fetchone()[0]

    if exists:
        return

    if not XLSX_PATH.exists():
        raise FileNotFoundError(f"Excel file not found at {XLSX_PATH}")

    df = pd.read_excel(XLSX_PATH, engine="openpyxl")
    con.register("enes_df", df)

    con.execute("""
        CREATE TABLE enes AS
        SELECT * FROM enes_df
    """)





