"""Coverage analysis: how many DB wave/question rows have a Vol A match."""
import sys, os, json, re

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'app'))

from data_store import get_conn, ensure_table
from vol_a import get_wave_sheet_map, get_question_index, _normalize_wave, _find_sheets_for_question

# --- Load DB rows ---
con = get_conn()
ensure_table(con)
rows = con.execute(
    'SELECT DISTINCT "Wave", "Question Number" FROM enes WHERE "Wave" IS NOT NULL AND "Question Number" IS NOT NULL'
).fetchall()
con.close()

wave_sheet_map = get_wave_sheet_map()
question_index = get_question_index()

total = len(rows)
no_file = 0
matched = 0
unmatched = []

for wave, question in rows:
    wave_str = str(wave).strip()
    q_str = str(question).strip()
    key = _normalize_wave(wave_str)
    if key not in wave_sheet_map:
        no_file += 1
        continue
    hits = _find_sheets_for_question(wave_str, q_str)
    if hits:
        matched += 1
    else:
        unmatched.append((wave_str, q_str))

with_file = total - no_file
print(f"Total distinct wave/question pairs : {total}")
print(f"  Waves with no Vol A file         : {no_file}")
print(f"  Waves with Vol A file            : {with_file}")
print(f"    Matched (Vol A found)          : {matched}")
print(f"    Unmatched (TOC shown)          : {len(unmatched)}  ({100*len(unmatched)/with_file:.1f}% of those with files)")
print()

# Group unmatched by wave
from collections import defaultdict
by_wave = defaultdict(list)
for w, q in unmatched:
    by_wave[w].append(q)

print("Unmatched questions by wave:")
for wave in sorted(by_wave, key=lambda w: float(re.search(r'(\d+\.?\d*)', w).group(1)) if re.search(r'(\d+\.?\d*)', w) else 0):
    qs = by_wave[wave]
    print(f"  {wave}: {len(qs)} unmatched — {', '.join(sorted(qs)[:15])}{'...' if len(qs)>15 else ''}")
