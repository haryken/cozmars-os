"""Điều khiển WireOS-style: assume, pad, camera MJPEG, mic 2 chiều, remote Cloudflare."""

from __future__ import annotations

import asyncio
import io
import os
import re
import shutil
import stat
import subprocess
import threading
import wave
from pathlib import Path
from typing import Optional

from aiohttp import WSMsgType, web

from cozmars.config import _home

CF_URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
CF_REL = "2025.2.1"
CF_ASSET = "https://github.com/cloudflare/cloudflared/releases/download/{ver}/cloudflared-linux-amd64"


def pcm16_wav(pcm: bytes, rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


class ControlSession:
    def __init__(self, wired) -> None:
        self.wired = wired
        self.assumed = False
        self.mirror = False
        self.head = 0.0
        self.lift = 0.0
        self.head_rate = 0.0
        self.lift_rate = 0.0
        self.cam_on = False
        self.remote = RemoteShare(wired)
        self._tick: Optional[asyncio.Task] = None

    def start_tick(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._tick is None or self._tick.done():
            self._tick = loop.create_task(self._servo_loop(), name="ctrl-servo")

    async def _servo_loop(self) -> None:
        dt = 0.05
        while True:
            if self.assumed:
                if self.head_rate:
                    self.head = max(-30.0, min(30.0, self.head + self.head_rate * dt))
                    self.wired.robot.head(self.head)
                if self.lift_rate:
                    self.lift = max(0.0, min(1.0, self.lift + self.lift_rate * dt))
                    self.wired.robot.lift(self.lift)
            await asyncio.sleep(dt)

    def assume(self) -> None:
        self.assumed = True
        self.wired.brain.mode = "teleop"
        self.wired.robot.stop()
        print("[CTRL] assume — teleop", flush=True)

    def release(self) -> None:
        self.assumed = False
        self.head_rate = 0.0
        self.lift_rate = 0.0
        self.mirror = False
        self.cam_on = False
        self.wired.robot.stop()
        if self.wired.brain.mode == "teleop":
            self.wired.brain.mode = "idle"
        print("[CTRL] release — idle", flush=True)

    def wheels(self, lw: float, rw: float) -> None:
        if not self.assumed:
            raise PermissionError("assume control first")
        left = max(-1.0, min(1.0, lw / 200.0))
        right = max(-1.0, min(1.0, rw / 200.0))
        self.wired.robot.speed(left, right)

    def set_lift_rate(self, speed: float) -> None:
        if not self.assumed:
            raise PermissionError("assume control first")
        self.lift_rate = float(speed) * 0.4

    def set_head_rate(self, speed: float) -> None:
        if not self.assumed:
            raise PermissionError("assume control first")
        self.head_rate = float(speed) * 12.0

    def say(self, text: str) -> None:
        if not self.assumed:
            raise PermissionError("assume control first")
        from cozmars.engines.cloud import google_tts

        google_tts.say(text, "vi")

    def play_wav(self, data: bytes) -> None:
        if not self.assumed:
            raise PermissionError("assume control first")
        from cozmars.engines.cloud.google_tts import play_bytes

        play_bytes("ctrl-wav", data, mime="audio/wav", lang="sfx", kind="sfx")

    def play_pcm(self, pcm: bytes, rate: int = 8000) -> None:
        if not pcm:
            return
        self.play_wav(pcm16_wav(pcm, rate))

    async def handle(self, request: web.Request, path: str) -> web.Response:
        q = request.query
        try:
            if path == "assume":
                self.assume()
                return web.json_response({"status": "ok"})
            if path == "release":
                self.release()
                return web.json_response({"status": "ok"})
            if path == "status":
                return web.json_response(
                    {
                        "assuming": self.assumed,
                        "cam": self.cam_on,
                        "mic": False,
                        "robotMic": False,
                    }
                )
            if path == "wheels":
                self.wheels(float(q.get("lw") or 0), float(q.get("rw") or 0))
                return web.json_response({"status": "ok"})
            if path == "lift":
                self.set_lift_rate(float(q.get("speed") or 0))
                return web.json_response({"status": "ok"})
            if path == "head":
                self.set_head_rate(float(q.get("speed") or 0))
                return web.json_response({"status": "ok"})
            if path == "say_text":
                text = (q.get("text") or "").strip()
                if not text:
                    return web.json_response({"status": "error", "message": "empty text"}, status=400)
                self.say(text)
                return web.json_response({"status": "ok"})
            if path == "play_sound":
                data = b""
                ctype = request.content_type or ""
                if "multipart" in ctype:
                    reader = await request.multipart()
                    while True:
                        part = await reader.next()
                        if part is None:
                            break
                        data = await part.read(decode=False)
                        if data:
                            break
                else:
                    data = await request.read()
                if not data:
                    return web.json_response({"status": "error", "message": "no audio"}, status=400)
                self.play_wav(data)
                return web.json_response({"status": "ok"})
            if path == "mirror":
                if not self.assumed:
                    raise PermissionError("assume control first")
                self.mirror = q.get("enable") in ("true", "1")
                print(f"[CTRL] mirror={self.mirror} (Cozmars không có LCD gương Vector)", flush=True)
                return web.json_response({"status": "ok"})
            if path == "stop_cam":
                self.cam_on = False
                return web.json_response({"status": "ok"})
            if path == "mic-stop":
                return web.json_response({"status": "ok"})
            if path == "robot-mic-stop":
                return web.json_response({"status": "ok"})
            if path == "remote-enable":
                return web.json_response(await self.remote.enable())
            if path == "remote-disable":
                return web.json_response(self.remote.disable())
            if path == "remote-status":
                return web.json_response(self.remote.snapshot())
        except PermissionError as exc:
            return web.json_response({"status": "error", "message": str(exc)}, status=403)
        except Exception as exc:  # noqa: BLE001
            return web.json_response({"status": "error", "message": str(exc)}, status=500)
        return web.json_response({"status": "error", "message": "404 not found"}, status=404)

    async def cam_mjpeg(self, request: web.Request) -> web.StreamResponse:
        cam = self.wired.camera
        resp = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "multipart/x-mixed-replace; boundary=frame",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
        await resp.prepare(request)
        self.cam_on = True
        try:
            while self.cam_on:
                tr = request.transport
                if tr is None or tr.is_closing():
                    break
                frame = b""
                if cam is not None:
                    try:
                        frame = await asyncio.to_thread(cam.capture)
                    except Exception:
                        frame = b""
                if frame:
                    ctype = "image/jpeg" if frame[:2] == b"\xff\xd8" else "image/png"
                    chunk = (
                        f"--frame\r\nContent-Type: {ctype}\r\nContent-Length: {len(frame)}\r\n\r\n".encode()
                        + frame
                        + b"\r\n"
                    )
                    await resp.write(chunk)
                await asyncio.sleep(0.12)
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            self.cam_on = False
        return resp

    async def ws_mic(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        if not self.assumed:
            await ws.send_str('{"error":"assume control first"}')
            await ws.close()
            return ws
        await ws.send_str('{"status":"ready","rate":8000}')
        buf = bytearray()
        try:
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    buf.extend(msg.data)
                    while len(buf) >= 3200:
                        chunk = bytes(buf[:3200])
                        del buf[:3200]
                        try:
                            self.play_pcm(chunk, 8000)
                        except PermissionError:
                            break
                elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        if buf:
            try:
                self.play_pcm(bytes(buf), 8000)
            except PermissionError:
                pass
        return ws

    async def ws_robot_mic(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        if not self.assumed:
            await ws.send_str('{"error":"assume control first"}')
            await ws.close()
            return ws
        await ws.send_str('{"status":"ready","rate":16000}')
        stop = asyncio.Event()

        async def wait_client() -> None:
            try:
                async for msg in ws:
                    if msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        break
            except (ConnectionResetError, asyncio.CancelledError):
                pass
            finally:
                stop.set()

        async def pump() -> None:
            sim = os.environ.get("COZMARS_SIM_URL", "").rstrip("/")
            silence = bytes(1920)
            last_err = ""
            import aiohttp

            timeout = aiohttp.ClientTimeout(total=None, sock_connect=4, sock_read=None)
            while not stop.is_set() and not ws.closed:
                if not sim:
                    if last_err != "no-sim":
                        last_err = "no-sim"
                        try:
                            await ws.send_str('{"error":"thiếu COZMARS_SIM_URL — bật mic trên sim :8088"}')
                        except Exception:
                            break
                    try:
                        await ws.send_bytes(silence)
                    except Exception:
                        break
                    await asyncio.sleep(1.0)
                    continue
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        url = sim.replace("http://", "ws://").replace("https://", "wss://") + "/api/mic-tap"
                        async with session.ws_connect(url, heartbeat=20) as src:
                            last_err = ""
                            async for msg in src:
                                if stop.is_set() or ws.closed:
                                    return
                                if msg.type == WSMsgType.BINARY and msg.data:
                                    await ws.send_bytes(msg.data)
                                elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                                    break
                except Exception as exc:  # noqa: BLE001
                    msg = str(exc).replace('"', "")[:120]
                    if msg != last_err:
                        last_err = msg
                        try:
                            await ws.send_str('{"error":"sim mic: ' + msg + '"}')
                        except Exception:
                            pass
                if stop.is_set() or ws.closed:
                    break
                try:
                    await ws.send_bytes(silence)
                except Exception:
                    break
                await asyncio.sleep(0.5)

        waiter = asyncio.create_task(wait_client())
        pumper = asyncio.create_task(pump())
        await stop.wait()
        waiter.cancel()
        pumper.cancel()
        return ws

    async def _proxy_arecord(self, ws: web.WebSocketResponse) -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "arecord",
                "-q",
                "-f",
                "S16_LE",
                "-r",
                "16000",
                "-c",
                "1",
                "-t",
                "raw",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except FileNotFoundError:
            await ws.send_str('{"error":"arecord missing"}')
            return
        try:
            while proc.stdout and not ws.closed:
                data = await proc.stdout.read(3200)
                if not data:
                    break
                await ws.send_bytes(data)
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            try:
                proc.kill()
            except Exception:
                pass


class RemoteShare:
    def __init__(self, wired) -> None:
        self.wired = wired
        self.phase = "idle"
        self.enabled = False
        self.url = ""
        self.error = ""
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "enabled": self.enabled,
                "url": self.url,
                "phase": self.phase,
                "error": self.error,
            }

    def _set(self, phase: str, **kw) -> None:
        with self._lock:
            self.phase = phase
            if "error" in kw:
                self.error = kw["error"]
            if "url" in kw:
                self.url = kw["url"]
            if "enabled" in kw:
                self.enabled = kw["enabled"]

    async def enable(self) -> dict:
        st = self.snapshot()
        if st["phase"] == "ready" and st["url"]:
            return st
        if st["phase"] in ("downloading", "starting"):
            return st
        self._set("starting", enabled=True, error="", url="")
        threading.Thread(target=self._run, daemon=True, name="cf-tunnel").start()
        return self.snapshot()

    def disable(self) -> dict:
        proc = self._proc
        self._proc = None
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
        self._set("idle", enabled=False, url="", error="")
        return self.snapshot()

    def _run(self) -> None:
        try:
            bin_path = _ensure_cloudflared(lambda msg: self._set("downloading", error=msg, enabled=True))
        except Exception as exc:  # noqa: BLE001
            self._set("error", enabled=False, error=str(exc))
            return
        self._set("starting", enabled=True, error="")
        port = 8099
        if self.wired.ports:
            port = int(self.wired.ports[0])
        try:
            proc = subprocess.Popen(
                [str(bin_path), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as exc:  # noqa: BLE001
            self._set("error", enabled=False, error=str(exc))
            return
        self._proc = proc
        url = ""
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                m = CF_URL_RE.search(line)
                if m:
                    url = m.group(0) + "/#control"
                    self._set("ready", enabled=True, url=url, error="")
                    print(f"[CTRL] remote {url}", flush=True)
                    break
        except Exception as exc:  # noqa: BLE001
            self._set("error", enabled=False, error=str(exc))
            return
        if not url:
            self._set("error", enabled=False, error="Không lấy được link trycloudflare")


def _ensure_cloudflared(progress) -> Path:
    found = shutil.which("cloudflared")
    if found:
        return Path(found)
    dest = _home() / "bin" / "cloudflared"
    if dest.exists() and os.access(dest, os.X_OK):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    progress("Đang tải cloudflared…")
    import urllib.request

    url = CF_ASSET.format(ver=CF_REL)
    tmp = dest.with_suffix(".tmp")
    try:
        urllib.request.urlretrieve(url, tmp)
        tmp.chmod(tmp.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        tmp.replace(dest)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise RuntimeError(
            "Không tải được cloudflared. Cài tay: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        ) from None
    return dest
