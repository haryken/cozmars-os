"""Web :80/:8080 (Pi) hoặc :8099 (sim). Firmware pages + OTA + Xiaozhi + games."""

from __future__ import annotations

import asyncio
from pathlib import Path

from cozmars.version import __version__

STATIC = Path(__file__).resolve().parent / "static"
FW_STATIC = Path(__file__).resolve().parent / "firmware_static"


class WiredEngine:
    name = "wired"

    def __init__(self, robot, brain, cloud=None, update=None, camera=None, host: str = "0.0.0.0", ports: tuple[int, ...] = (80, 8080)) -> None:
        self.robot = robot
        self.brain = brain
        self.cloud = cloud
        self.update = update
        self.camera = camera
        self.host = host
        self.ports = ports
        self._runner = None
        self._wifi_runner = None
        from .control import ControlSession

        self.ctrl = ControlSession(self)

    async def start(self) -> None:
        try:
            from aiohttp import web
        except Exception as exc:  # noqa: BLE001
            print(f"[WIRED] MISS aiohttp — {exc}", flush=True)
            return

        async def index(_r):
            from . import wifi_portal

            if wifi_portal.is_hotspot_mode():
                raise web.HTTPFound("/wifi")
            return web.FileResponse(STATIC / "index.html")

        async def about(_r):
            slots = self.update.slot_info() if self.update else {}
            return web.json_response(
                {
                    "os": "cozmars-os",
                    "version": __version__,
                    "engines": ["robot", "anim", "engine", "cloud", "switchboard", "wired", "camera", "update"],
                    "hal": getattr(self.robot.hal, "name", "?"),
                    "wifi_portal": 8077,
                    "wifi_hotspot_ip": "10.3.141.1",
                    "wifi_hotspot_open": True,
                    "slots": slots,
                }
            )

        async def api_update(request):
            url = request.query.get("url", "")
            try:
                body = await request.json()
                url = body.get("url") or url
            except Exception:
                pass
            if not self.update:
                return web.json_response({"ok": False, "reason": "no update engine"})
            return web.json_response(await self.update.start(url))

        async def api_update_status(_request):
            if not self.update:
                return web.json_response({"ok": False, "reason": "no update engine"})
            return web.json_response(self.update.status())

        async def api_voice(request):
            from ..cloud import xiaozhi as xz

            body = await request.json()
            mode = body.get("mode", "off")
            cfg = xz.load_cfg()
            changed = False
            if body.get("ota_base_url"):
                cfg["ota_base_url"] = str(body["ota_base_url"]).rstrip("/") + "/"
                changed = True
            if body.get("identity_mode") in ("vi_pool", "custom"):
                cfg["identity_mode"] = body["identity_mode"]
                changed = True
            if changed:
                xz.save_cfg(cfg)
            if self.cloud:
                self.cloud.set_mode(mode)
            return web.json_response({"ok": True, "mode": mode, "config": xz.load_cfg()})

        async def api_xiaozhi(_r):
            from ..cloud import xiaozhi as xz

            cfg = xz.load_cfg()
            cfg["voice_mode"] = getattr(self.cloud, "mode", "")
            return web.json_response(cfg)

        async def api_xiaozhi_activate(request):
            from ..cloud import xiaozhi as xz

            identity = "custom"
            new_device = False
            try:
                body = await request.json()
                identity = str(body.get("identity_mode") or identity)
                new_device = bool(body.get("new_device"))
            except Exception:
                pass
            out = xz.generate_code(identity_mode=identity, new_device=new_device)
            status = 200 if out.get("status") != "error" else 400
            return web.json_response(out, status=status)

        async def api_wake(request):
            import asyncio

            body = await request.json()
            source = str(body.get("source") or "mic")
            text = str(body.get("text") or "")
            if not self.cloud:
                return web.json_response({"ok": False, "reason": "no cloud"})

            async def _run() -> None:
                try:
                    await self.cloud.handle_wake(source, text)
                except Exception as exc:  # noqa: BLE001
                    print(f"[CLOUD] wake task fail: {exc}", flush=True)

            asyncio.create_task(_run(), name="xz-wake")
            return web.json_response({"ok": True, "path": "xiaozhi", "started": True})

        async def api_tts_idle(_request):
            from ..cloud import xiaozhi as xz

            xz.notify_tts_idle()
            return web.json_response({"ok": True})

        async def api_mic(request):
            import base64

            from ..cloud import xiaozhi as xz

            try:
                body = await request.json()
            except Exception:
                return web.json_response({"ok": False, "reason": "bad json"}, status=400)
            if body.get("end"):
                xz.end_pcm()
                return web.json_response({"ok": True, "end": True})
            b64 = str(body.get("pcm") or "")
            if not b64:
                return web.json_response({"ok": False, "reason": "empty"})
            try:
                raw = base64.b64decode(b64)
            except Exception:
                return web.json_response({"ok": False, "reason": "b64"}, status=400)
            return web.json_response({"ok": xz.push_pcm(raw), "n": len(raw)})

        async def api_intent(request):
            body = await request.json()
            self.brain.handle_intent(body.get("name", "intent_imperative_halt"), body.get("params") or {})
            return web.json_response({"ok": True})

        async def api_mods(request):
            from .games import handle

            name = request.match_info["name"]
            path = request.match_info.get("path") or "state"
            if name == "Control":
                return await self.ctrl.handle(request, path)
            if name == "JdocSettings":
                from . import settings_api

                return await settings_api.handle(self, request, path)
            uci = request.query.get("uci", "")
            if request.method == "POST":
                try:
                    body = await request.json()
                    uci = body.get("uci") or uci
                except Exception:
                    post = await request.post()
                    uci = post.get("uci", uci)
            try:
                return web.json_response(handle(name, path, uci=uci))
            except ValueError as exc:
                return web.json_response({"status": "error", "message": str(exc)}, status=400)

        from . import wifi_portal

        app = web.Application(client_max_size=8 * 1024 * 1024, middlewares=[wifi_portal.captive_middleware()])
        wifi_portal.attach_routes(app)
        app.router.add_get("/", index)
        app.router.add_get("/about", about)
        app.router.add_post("/api/update", api_update)
        app.router.add_get("/api/update", api_update)
        app.router.add_get("/api/update/status", api_update_status)
        app.router.add_post("/api/voice", api_voice)
        app.router.add_get("/api/xiaozhi", api_xiaozhi)
        app.router.add_post("/api/xiaozhi/activate", api_xiaozhi_activate)
        app.router.add_post("/api/xiaozhi/generate_code", api_xiaozhi_activate)
        app.router.add_post("/api/wake", api_wake)
        app.router.add_post("/api/tts_idle", api_tts_idle)
        app.router.add_post("/api/mic", api_mic)
        app.router.add_post("/api/intent", api_intent)
        app.router.add_get("/api/mods/Control/cam-stream", self.ctrl.cam_mjpeg)
        app.router.add_get("/api/mods/Control/mic-stream", self.ctrl.ws_mic)
        app.router.add_get("/api/mods/Control/robot-mic-stream", self.ctrl.ws_robot_mic)
        app.router.add_route("*", "/api/mods/{name}/{path}", api_mods)
        if STATIC.is_dir():
            app.router.add_static("/static", STATIC)
        if FW_STATIC.is_dir():
            app.router.add_static("/fw", FW_STATIC)

        started = []
        for port in self.ports:
            try:
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, self.host, port)
                await site.start()
                started.append(port)
                self._runner = runner
            except OSError as exc:
                print(f"[WIRED] bind :{port} fail — {exc}", flush=True)
        if started:
            self.ctrl.start_tick(asyncio.get_running_loop())
            print(f"[WIRED] http://{self.host}:{started[0]}/  ports={started}", flush=True)
        else:
            print("[WIRED] không bind được port", flush=True)

        # Portal WiFi riêng :8077 — LAN và hotspot đều vào được
        from . import wifi_portal

        self._wifi_runner = await wifi_portal.start_portal(self.host, wifi_portal.WIFI_PORT)

    async def stop(self) -> None:
        if self._wifi_runner:
            await self._wifi_runner.cleanup()
            self._wifi_runner = None
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
