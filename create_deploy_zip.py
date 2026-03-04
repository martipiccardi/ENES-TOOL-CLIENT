"""Creates deploy.zip with Linux-compatible forward-slash paths."""
import zipfile, os, glob, sys

TEXT_EXTS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.json',
             '.txt', '.sh', '.md', '.svg', '.yml', '.yaml'}

zip_path = 'deploy.zip'

if os.path.exists(zip_path):
    os.remove(zip_path)

entries = []

# Backend Python files
for root, dirs, files in os.walk('backend'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        fpath = os.path.join(root, f)
        arc = fpath.replace(os.sep, '/')
        entries.append((fpath, arc))

# Data files
for root, dirs, files in os.walk('data'):
    for f in files:
        fpath = os.path.join(root, f)
        arc = fpath.replace(os.sep, '/')
        entries.append((fpath, arc))

# Frontend dist
for root, dirs, files in os.walk(os.path.join('frontend', 'dist')):
    for f in files:
        fpath = os.path.join(root, f)
        arc = fpath.replace(os.sep, '/')
        entries.append((fpath, arc))

# Root files
for f in ['startup.sh', 'requirements.txt']:
    if os.path.exists(f):
        entries.append((f, f))

total = len(entries)
print(f'Zipping {total} files...')

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for i, (src, dst) in enumerate(entries):
        if not os.path.exists(src):
            print(f'  SKIP (missing): {src}')
            continue
        ext = os.path.splitext(src)[1].lower()
        if ext in TEXT_EXTS:
            try:
                with open(src, 'r', encoding='utf-8') as f:
                    content = f.read()
                zf.writestr(dst, content.replace('\r\n', '\n'))
            except Exception:
                zf.write(src, dst)
        else:
            zf.write(src, dst)
        if (i + 1) % 50 == 0 or i + 1 == total:
            print(f'  {i+1}/{total}')

size_mb = os.path.getsize(zip_path) / (1024*1024)
print(f'Done. deploy.zip = {size_mb:.1f} MB')
