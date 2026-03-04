"""
Build deploy.zip with forward-slash paths and Linux-safe shell scripts.

Fixes two Windows-specific issues that break Azure Kudu/Linux:
1. Compress-Archive uses backslash paths in ZIP entries → rsync fails
2. Shell scripts have CRLF endings → #!/bin/bash\r shebang → "not found"

This script uses Python's zipfile module (always forward-slash paths) and
converts .sh files to LF and marks them executable (0o755).

Usage:
    python make_deploy_zip.py
"""

import sys
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
OUT_ZIP = ROOT / "deploy.zip"

INCLUDES = [
    ROOT / "backend",
    ROOT / "data",
    ROOT / "frontend" / "dist",
    ROOT / "requirements.txt",
    ROOT / "startup.sh",
]

# Sanity checks
missing = [p for p in INCLUDES if not p.exists()]
if missing:
    for m in missing:
        print(f"ERROR: missing required path: {m}", file=sys.stderr)
    sys.exit(1)

if OUT_ZIP.exists():
    OUT_ZIP.unlink()
    print(f"Removed old {OUT_ZIP.name}")

print("Building deploy.zip ...")
total_files = 0


def add_file(zf: zipfile.ZipFile, fpath: Path, arcname: str) -> None:
    """Add a file to the ZIP, converting .sh files to LF and marking executable."""
    data = fpath.read_bytes()

    info = zipfile.ZipInfo(arcname)
    info.compress_type = zipfile.ZIP_DEFLATED

    if arcname.endswith(".sh"):
        # Strip carriage returns so shebang is #!/bin/bash (not #!/bin/bash\r)
        data = data.replace(b"\r\n", b"\n")
        # Unix execute + read/write for owner, read/execute for group+other (0o755)
        info.external_attr = (stat.S_IFREG | 0o755) << 16
    else:
        info.external_attr = (stat.S_IFREG | 0o644) << 16

    zf.writestr(info, data)


with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for source in INCLUDES:
        if source.is_file():
            arcname = source.name  # e.g. requirements.txt, startup.sh
            add_file(zf, source, arcname)
            total_files += 1
        else:
            # Directory: walk and add files with forward-slash arcnames
            for fpath in source.rglob("*"):
                if fpath.is_file():
                    rel = fpath.relative_to(ROOT)
                    arcname = rel.as_posix()  # guaranteed forward slashes
                    add_file(zf, fpath, arcname)
                    total_files += 1

size_mb = OUT_ZIP.stat().st_size / (1024 * 1024)
print(f"Done: {total_files} files, {size_mb:.1f} MB -> {OUT_ZIP}")
