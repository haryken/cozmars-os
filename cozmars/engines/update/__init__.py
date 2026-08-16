"""OTA: tải http(s) .tgz — source hoặc arm-bundle (không pip)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import tarfile
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
        tree = dest / "tree"
        if tree.exists():
            import shutil

            shutil.rmtree(tree, ignore_errors=True)
        tree.mkdir(parents=True, exist_ok=True)
        try:
            with tarfile.open(tgz, "r:*") as tar:
                try:
                    tar.extractall(tree, filter="data")
                except TypeError:
                    tar.extractall(tree)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": f"untar: {exc}"}
        man_paths = list(tree.rglob("MANIFEST.json"))
        sha = hashlib.sha256(tgz.read_bytes()).hexdigest()
        kind = "source"
        ver = __version__
        if man_paths:
            try:
                man = json.loads(man_paths[0].read_text(encoding="utf-8"))
                kind = str(man.get("kind") or "source")
                ver = str(man.get("version") or ver)
            except Exception:
                pass
        print(f"[UPDATE] extracted sha256={sha[:12]} kind={kind} ver={ver}", flush=True)

        if kind == "arm-bundle":
            return await self._install_fat(tgz, sha, ver)
        print(
            "[UPDATE] gói source — trên Pi dùng bootstrap/install-pi hoặc nạp arm-bundle; sim không pip",
            flush=True,
        )
        return {"ok": True, "sha256": sha, "kind": kind, "current": __version__, "version": ver}

    async def _install_fat(self, tgz: Path, sha: str, ver: str) -> dict:
        """Giải nén bundle → /opt/cozmars, không pip."""
        if os.environ.get("COZMARS_HAL") == "sim" or not Path("/etc/systemd/system").is_dir():
            print("[UPDATE] arm-bundle trên sim — chỉ verify, không ghi /opt", flush=True)
            return {"ok": True, "sha256": sha, "kind": "arm-bundle", "version": ver, "installed": False, "sim": True}
        script = Path(__file__).resolve().parents[3] / "scripts" / "install-fat.sh"
        if not script.is_file():
            alt = Path("/opt/cozmars/install-fat.sh")
            script = alt if alt.is_file() else script
        if not script.is_file():
            return {"ok": False, "reason": "thiếu install-fat.sh"}
        print(f"[UPDATE] install-fat {tgz}", flush=True)

        def _run() -> subprocess.CompletedProcess:
            return subprocess.run(
                ["bash", str(script), str(tgz)],
                capture_output=True,
                text=True,
                timeout=300,
            )

        try:
            proc = await asyncio.get_event_loop().run_in_executor(None, _run)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": str(exc)}
        if proc.stdout:
            print(proc.stdout[-2000:], flush=True)
        if proc.returncode != 0:
            print(proc.stderr[-1000:] if proc.stderr else "", flush=True)
            return {"ok": False, "reason": f"install-fat exit {proc.returncode}", "log": (proc.stderr or "")[-500:]}
        print("[UPDATE] arm-bundle installed — restart cozmars", flush=True)
        try:
            subprocess.run(["systemctl", "restart", "cozmars.service"], check=False, timeout=30)
        except Exception:
            pass
        return {"ok": True, "sha256": sha, "kind": "arm-bundle", "version": ver, "installed": True}
