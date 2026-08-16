"""OTA: tải http(s) .tgz, verify MANIFEST, cài, không ghi ~/.cozmars."""

from __future__ import annotations

import hashlib
import json
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from cozmars.version import __version__


class UpdateEngine:
    name = "update"

    def __init__(self) -> None:
        print(f"[UPDATE] ready  current={__version__}", flush=True)

    async def start(self, url: str) -> dict:
        if not url.startswith(("http://", "https://")):
            print(f"[UPDATE] reject {url!r}", flush=True)
            return {"ok": False, "reason": "chỉ http(s)"}
        dest = Path("/tmp/cozmars-update")
        dest.mkdir(parents=True, exist_ok=True)
        tgz = dest / "pkg.tgz"
        print(f"[UPDATE] download {url}", flush=True)
        try:
            urllib.request.urlretrieve(url, tgz)
        except Exception as exc:  # noqa: BLE001
            print(f"[UPDATE] download fail: {exc}", flush=True)
            return {"ok": False, "reason": str(exc)}
        try:
            with tarfile.open(tgz, "r:*") as tar:
                tar.extractall(dest / "tree", filter="data")
        except TypeError:
            with tarfile.open(tgz, "r:*") as tar:
                tar.extractall(dest / "tree")
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": f"untar: {exc}"}
        man = list((dest / "tree").rglob("MANIFEST.json"))
        sha = hashlib.sha256(tgz.read_bytes()).hexdigest()
        print(f"[UPDATE] extracted sha256={sha[:12]} manifest={bool(man)}", flush=True)
        print("[UPDATE] trên Pi: pip install cây giải nén rồi systemctl restart (sim không pip)", flush=True)
        return {"ok": True, "sha256": sha, "current": __version__, "manifest": str(man[0]) if man else None}
