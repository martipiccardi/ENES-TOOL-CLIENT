import sys, re, os
sys.path.insert(0, 'backend/app')
import openpyxl
from data_store import get_conn, ensure_table
from vol_a import get_wave_sheet_map

sm = get_wave_sheet_map()
fpath = [f for f in sm.get('93.2', {}).keys() if 'CAP' in f][0]
print('File:', os.path.basename(fpath))

# Get first 8 English texts from Content sheet col2
wb = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
ws = wb['Content']
in_data = False
content_rows = []
for row in ws.iter_rows(values_only=True):
    if not row: continue
    col0 = str(row[0]).strip() if row[0] else ''
    if col0.lower() == 'sheet': in_data = True; continue
    if not in_data: continue
    if col0 and len(row) > 2 and row[2]:
        content_rows.append((col0, str(row[2]).strip()))
    if len(content_rows) >= 8: break
wb.close()

print('Content sheet col2 (English) - full text:')
for t, eng in content_rows:
    print(f'  {t}: {eng}')

# Get DB questions for EB93.2 first several questions
con = get_conn()
ensure_table(con)
rows = con.execute(
    'SELECT "Question Number", "Question(s)" FROM enes WHERE "Wave" LIKE \'%93.2%\' ORDER BY "Question Number" LIMIT 15'
).fetchall()
con.close()
print()
print('DB questions for EB93.2 (first 15):')
for qn, text in rows:
    print(f'  {qn}: {str(text)[:120]}')
