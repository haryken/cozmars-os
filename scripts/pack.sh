#!/usr/bin/env bash
# Pack OTA tarball: dist/cozmars-<ver>.tgz  (không kèm ~/.cozmars conf)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="$(python3 -c "import sys; sys.path.insert(0,'$ROOT'); from cozmars.version import __version__; print(__version__)")"
OUT="$ROOT/dist"
STAGE="$(mktemp -d)"
mkdir -p "$OUT" "$STAGE/cozmars-os"
trap 'rm -rf "$STAGE"' EXIT
rsync -a --delete \
  --exclude '.git' --exclude 'dist' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.venv' --exclude 'assets/vosk' \
  "$ROOT/" "$STAGE/cozmars-os/"
python3 - <<PY
import hashlib, json, pathlib
root = pathlib.Path("$STAGE/cozmars-os")
files = []
h = hashlib.sha256()
for p in sorted(root.rglob("*")):
    if p.is_file():
        rel = str(p.relative_to(root))
        data = p.read_bytes()
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "n": len(data)})
        h.update(data)
manifest = {"name": "cozmars-os", "version": "$VER", "sha256": h.hexdigest(), "files": len(files)}
(root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("MANIFEST", manifest["sha256"][:12], "files", manifest["files"])
PY
TGZ="$OUT/cozmars-$VER.tgz"
tar -C "$STAGE" -czf "$TGZ" cozmars-os
echo "packed $TGZ ($(wc -c < "$TGZ") bytes)"
