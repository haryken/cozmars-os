"""OTA http(s) → arm-bundle vào slot A/B nghỉ; progress + status cho web."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import tarfile
import threading
import time
import urllib.request
from pathlib import Path

from cozmars.version import __version__

STATE_DIR = Path(os.environ.get("COZMARS_UPDATE_STATE", "/run/cozmars-update"))
ETC = Path("/etc/cozmars")


def _read_text(p: Path, default: str = "") -> str:
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        return default


class UpdateEngine:
    name = "update"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._task: asyncio.Task | None = None
        self._state: dict = {
            "phase": "idle",
            "percent": 0,
            "done": False,
            "error": "",
            "url": "",
            "kind": "",
            "version": "",
            "sha256": "",
            "current": __version__,
            "active_slot": self.slot_info().get("active", ""),
            "log": [],
        }
        print(f"[UPDATE] ready  current={__version__} slots={self.slot_info()}", flush=True)

    def slot_info(self) -> dict:
        active = _read_text(ETC / "active-slot", "")
        previous = _read_text(ETC / "previous-slot", "")
        boot_state = _read_text(ETC / "boot-state", "")
        boot_tries = _read_text(ETC / "boot-tries", "0")
        link = Path("/opt/cozmars")
        link_target = ""
        try:
            if link.is_symlink():
                link_target = os.readlink(link)
            elif link.is_dir():
                link_target = "(legacy-dir)"
        except Exception:
            pass
        return {
            "active": active or "?",
            "previous": previous,
            "boot_state": boot_state or "?",
            "boot_tries": boot_tries,
            "link": str(link),
            "link_target": link_target,
            "slots": {
                "a": Path("/opt/cozmars-a").is_dir(),
                "b": Path("/opt/cozmars-b").is_dir(),
            },
        }

    def mark_boot_ok(self) -> None:
        """Gọi sau khi engines lên — xác nhận slot pending."""
        if not ETC.is_dir() and not Path("/etc/systemd/system").is_dir():
            return
        try:
            ETC.mkdir(parents=True, exist_ok=True)
            (ETC / "boot-state").write_text("ok\n", encoding="utf-8")
            (ETC / "boot-tries").write_text("0\n", encoding="utf-8")
            print(f"[UPDATE] boot-ok slot={self.slot_info().get('active')}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[UPDATE] boot-ok skip: {exc}", flush=True)

    def status(self) -> dict:
        st = dict(self._state)
        # Merge file progress từ install-fat (nếu có)
        pct_f = STATE_DIR / "percent"
        phase_f = STATE_DIR / "phase"
        if pct_f.is_file() and st.get("phase") not in ("idle", "done", "error"):
            try:
                st["percent"] = max(int(st.get("percent") or 0), int(_read_text(pct_f, "0") or 0))
            except ValueError:
                pass
        if phase_f.is_file() and st.get("phase") not in ("idle", "done", "error"):
            ph = _read_text(phase_f)
            if ph:
                st["phase"] = ph
        st["slots"] = self.slot_info()
        st["current"] = __version__
        st["busy"] = bool(self._task and not self._task.done())
        return st

    def _set(self, **kw) -> None:
        with self._lock:
            self._state.update(kw)
            if "phase" in kw or "percent" in kw:
                line = f"{self._state.get('percent', 0)}% {self._state.get('phase', '')}"
                log = list(self._state.get("log") or [])
                if not log or log[-1] != line:
                    log.append(line)
                    self._state["log"] = log[-80:]
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            (STATE_DIR / "status.json").write_text(
                json.dumps(self.status(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    async def start(self, url: str) -> dict:
        """Bắt đầu OTA nền — trả về ngay để UI poll /api/update/status."""
        if not url.startswith(("http://", "https://")):
            return {"ok": False, "reason": "chỉ http(s)"}
        if self._task and not self._task.done():
            return {"ok": False, "reason": "đang cập nhật", "status": self.status()}
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        for name in ("percent", "phase", "result.json"):
            p = STATE_DIR / name
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
        self._set(
            phase="starting",
            percent=0,
            done=False,
            error="",
            url=url,
            kind="",
            version="",
            sha256="",
            log=[],
            active_slot=self.slot_info().get("active", ""),
        )
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run(url))
        return {"ok": True, "started": True, "status": self.status()}

    async def _run(self, url: str) -> None:
        try:
            result = await self._do_update(url)
            if result.get("ok"):
                self._set(
                    phase="done",
                    percent=100,
                    done=True,
                    error="",
                    kind=result.get("kind", ""),
                    version=result.get("version", ""),
                    sha256=result.get("sha256", ""),
                )
            else:
                self._set(
                    phase="error",
                    done=True,
                    error=str(result.get("reason") or "fail"),
                    percent=int(self._state.get("percent") or 0),
                )
        except Exception as exc:  # noqa: BLE001
            print(f"[UPDATE] crash: {exc}", flush=True)
            self._set(phase="error", done=True, error=str(exc))

    async def _do_update(self, url: str) -> dict:
        dest = Path("/tmp/cozmars-update")
        dest.mkdir(parents=True, exist_ok=True)
        tgz = dest / "pkg.tgz"
        self._set(phase="download", percent=1)
        print(f"[UPDATE] download {url}", flush=True)

        def _download() -> None:
            last_pct = [-1]

            def hook(blocknum: int, blocksize: int, totalsize: int) -> None:
                if totalsize <= 0:
                    got = blocknum * blocksize
                    pct = min(45, 1 + (got // (512 * 1024)))
                else:
                    pct = int(min(48, max(1, (blocknum * blocksize * 48) // totalsize)))
                if pct != last_pct[0]:
                    last_pct[0] = pct
                    self._set(phase="download", percent=pct)

            urllib.request.urlretrieve(url, tgz, reporthook=hook)

        try:
            await asyncio.get_event_loop().run_in_executor(None, _download)
        except Exception as exc:  # noqa: BLE001
            print(f"[UPDATE] download fail: {exc}", flush=True)
            return {"ok": False, "reason": str(exc)}

        self._set(phase="extract", percent=50)
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
        self._set(kind=kind, version=ver, sha256=sha, percent=52, phase="extracted")

        if kind == "arm-bundle":
            return await self._install_fat(tgz, sha, ver)
        print(
            "[UPDATE] gói source — trên Pi dùng arm-bundle (A/B); sim không pip",
            flush=True,
        )
        return {"ok": True, "sha256": sha, "kind": kind, "current": __version__, "version": ver}

    async def _install_fat(self, tgz: Path, sha: str, ver: str) -> dict:
        if os.environ.get("COZMARS_HAL") == "sim" or not Path("/etc/systemd/system").is_dir():
            print("[UPDATE] arm-bundle trên sim — verify only (A/B không ghi)", flush=True)
            self._set(phase="sim-verify", percent=100, done=True)
            return {
                "ok": True,
                "sha256": sha,
                "kind": "arm-bundle",
                "version": ver,
                "installed": False,
                "sim": True,
                "slots": self.slot_info(),
            }

        script = Path(__file__).resolve().parents[3] / "scripts" / "install-fat.sh"
        if not script.is_file():
            alt = Path("/opt/cozmars/install-fat.sh")
            script = alt if alt.is_file() else script
        if not script.is_file():
            src_alt = Path("/opt/cozmars/src/scripts/install-fat.sh")
            script = src_alt if src_alt.is_file() else script
        if not script.is_file():
            return {"ok": False, "reason": "thiếu install-fat.sh"}

        self._set(phase="install-ab", percent=55)
        env = os.environ.copy()
        env["COZMARS_UPDATE_STATE"] = str(STATE_DIR)

        def _run() -> subprocess.CompletedProcess:
            return subprocess.run(
                ["bash", str(script), str(tgz)],
                capture_output=True,
                text=True,
                timeout=600,
                env=env,
            )

        loop = asyncio.get_event_loop()
        fut = loop.run_in_executor(None, _run)
        try:
            while not fut.done():
                pct = _read_text(STATE_DIR / "percent", "")
                ph = _read_text(STATE_DIR / "phase", "")
                try:
                    if pct:
                        self._set(percent=max(55, min(99, int(pct))), phase=ph or "install-ab")
                except ValueError:
                    if ph:
                        self._set(phase=ph)
                await asyncio.sleep(0.4)
            proc = await fut
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": str(exc)}
        if proc.stdout:
            print(proc.stdout[-2000:], flush=True)
        if proc.returncode != 0:
            print(proc.stderr[-1000:] if proc.stderr else "", flush=True)
            return {
                "ok": False,
                "reason": f"install-fat exit {proc.returncode}",
                "log": (proc.stderr or "")[-500:],
            }

        print("[UPDATE] A/B install ok — service restarting", flush=True)
        time.sleep(0.5)
        return {
            "ok": True,
            "sha256": sha,
            "kind": "arm-bundle",
            "version": ver,
            "installed": True,
            "slots": self.slot_info(),
        }
