"""Trang cấu hình WiFi — :8077 (LAN) và /wifi (hotspot 10.3.141.1)."""

from __future__ import annotations

import asyncio
import os
import re
import socket
import subprocess
import uuid
from pathlib import Path

WPA_CONF = Path("/etc/wpa_supplicant/wpa_supplicant.conf")
SAVE_SH = Path(__file__).resolve().parent / "save_wifi.sh"
HOTSPOT_IP = "10.3.141.1"
WIFI_PORT = int(os.environ.get("COZMARS_WIFI_PORT", "8077"))


def serial() -> str:
    return hex(uuid.getnode())[2:].zfill(12)[-4:].upper()


def hostname() -> str:
    try:
        return socket.gethostname() or "cozmars"
    except Exception:
        return "cozmars"


def lan_ips() -> list[str]:
    out: list[str] = []
    try:
        for line in subprocess.check_output(["hostname", "-I"], text=True, timeout=2).split():
            ip = line.strip()
            if ip and not ip.startswith("127.") and ip not in out:
                out.append(ip)
    except Exception:
        pass
    return out


def is_hotspot_mode() -> bool:
    return HOTSPOT_IP in lan_ips()


def read_ssid() -> str:
    if not WPA_CONF.is_file():
        return ""
    try:
        text = WPA_CONF.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    m = re.search(r'^\s*ssid\s*=\s*"([^"]*)"', text, re.M)
    return m.group(1) if m else ""


def ensure_wpa_conf() -> None:
    if WPA_CONF.is_file():
        return
    WPA_CONF.parent.mkdir(parents=True, exist_ok=True)
    WPA_CONF.write_text(
        "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n"
        "update_config=1\ncountry=VN\n\n"
        'network={\n\tssid="wifi_name"\n\tpsk="wifi_password"\n}\n',
        encoding="utf-8",
    )
    try:
        os.chmod(WPA_CONF, 0o600)
    except OSError:
        pass


def save_credentials(ssid: str, password: str) -> None:
    ensure_wpa_conf()
    ssid = ssid.strip()
    password = password.strip()
    if not ssid:
        raise ValueError("SSID trống")
    if len(password) < 8:
        raise ValueError("Mật khẩu WiFi phải ≥ 8 ký tự")
    # Chặn injection shell
    if any(c in ssid + password for c in ("\n", "\r", '"', "`", "$", "\\")):
        raise ValueError("SSID/mật khẩu chứa ký tự không hợp lệ")
    subprocess.check_call(["bash", str(SAVE_SH), ssid, password], timeout=10)


def restart_network() -> None:
    """Thử autohotspot trước; fallback wpa/dhcpcd."""
    for cmd in (
        ["systemctl", "restart", "cozmars-autohotspot.service"],
        ["systemctl", "restart", "autohotspot.service"],
        ["bash", "/usr/local/bin/cozmars-autohotspot"],
        ["systemctl", "restart", "wpa_supplicant"],
        ["systemctl", "restart", "dhcpcd"],
    ):
        try:
            subprocess.check_call(cmd, timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception:
            continue


def page_html(ssid: str = "", saved: bool = False, err: str = "") -> str:
    host = hostname()
    ser = serial()
    ips = lan_ips()
    hotspot = is_hotspot_mode()
    mode = "Hotspot mở — chọn WiFi nhà bên dưới" if hotspot else "Đã có mạng LAN"
    pill_cls = "pill is-hotspot" if hotspot else "pill"
    links = []
    for ip in ips:
        if ip == HOTSPOT_IP:
            continue
        links.append(("LAN", f"http://{ip}:{WIFI_PORT}/"))
    links.append(("mDNS", f"http://{host}.local:{WIFI_PORT}/"))
    link_items = "".join(
        f'<li><span class="lbl">{lbl}</span><a href="{url}">{url}</a></li>' for lbl, url in links
    )
    banner = ""
    if saved:
        banner = (
            '<div class="alert ok">Đã lưu. Bấm <b>Áp dụng mạng</b> — robot thử nối WiFi nhà rồi tắt hotspot.</div>'
        )
    if err:
        err_esc = (
            str(err).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        banner = f'<div class="alert err">{err_esc}</div>'
    ssid_esc = (
        ssid.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    hotspot_card = ""
    if hotspot:
        hotspot_card = f"""
  <section class="card">
    <h2>Hotspot robot</h2>
    <div class="meta">
      <div class="meta-row"><span>SSID</span><strong><code>{host}</code></strong></div>
      <div class="meta-row"><span>Mật khẩu</span><strong>Không — mạng mở</strong></div>
    </div>
    <p class="hint">Điện thoại vừa nối sẽ tự mở trang này (captive portal).</p>
  </section>"""
    else:
        hotspot_card = f"""
  <section class="card">
    <h2>Robot</h2>
    <div class="meta">
      <div class="meta-row"><span>Hostname</span><strong><code>{host}</code></strong></div>
      <div class="meta-row"><span>Serial</span><strong><code>{ser}</code></strong></div>
      <div class="meta-row"><span>Khi mất mạng</span><strong>Hotspot mở <code>{host}</code> (không MK)</strong></div>
    </div>
  </section>

  <section class="card">
    <h2>Mở trang này</h2>
    <ul class="link-list">
      <li><span class="lbl">Hotspot</span><a href="http://{HOTSPOT_IP}/wifi">http://{HOTSPOT_IP}/wifi</a></li>
      <li><span class="lbl">Hotspot :8077</span><a href="http://{HOTSPOT_IP}:{WIFI_PORT}/">http://{HOTSPOT_IP}:{WIFI_PORT}/</a></li>
      {link_items}
    </ul>
  </section>"""

    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#070c10">
<title>Cozmars · WiFi</title>
<link rel="icon" type="image/svg+xml" href="/static/cozmars-logo.svg">
<link rel="stylesheet" href="/static/wifi.css">
</head>
<body>
<main class="wrap">
  <header class="hero">
    <img class="logo" src="/static/cozmars-logo.svg" width="72" height="72" alt="Cozmars">
    <h1>Cozmars</h1>
    <p class="tag">Cấu hình WiFi nhà · chỉ 2.4&nbsp;GHz</p>
    <div class="{pill_cls}"><span class="dot" aria-hidden="true"></span>{mode}</div>
  </header>

  {hotspot_card}

  {banner}

  <section class="card">
    <h2>WiFi nhà</h2>
    <form method="post" action="/save_wifi" onsubmit="return check()">
      <div class="field">
        <label for="ssid">Tên WiFi (SSID) <span class="sub">· không dùng băng 5&nbsp;GHz</span></label>
        <input id="ssid" type="text" name="ssid" value="{ssid_esc}" required autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Tên mạng WiFi">
      </div>
      <div class="field">
        <label for="pass">Mật khẩu WiFi nhà</label>
        <div class="pass-row">
          <input id="pass" type="password" name="pass" value="" minlength="8" required autocomplete="current-password" placeholder="Ít nhất 8 ký tự">
          <button type="button" class="btn-ghost" id="eye" onclick="toggle()">Hiện</button>
        </div>
      </div>
      <div class="actions">
        <button type="submit" class="btn btn-secondary">Lưu</button>
        <button type="submit" class="btn btn-primary" formaction="/restart_wifi" formmethod="post">Áp dụng mạng</button>
      </div>
    </form>
  </section>

  <p class="foot">Sau khi áp dụng, chờ 30–60 giây rồi mở <code>http://{host}.local/</code></p>
</main>
<script>
function toggle(){{
  var p=document.getElementById('pass'),e=document.getElementById('eye');
  if(p.type==='password'){{p.type='text';e.textContent='Ẩn';}}
  else{{p.type='password';e.textContent='Hiện';}}
}}
function check(){{
  var p=document.getElementById('pass');
  if(p.value.length<8){{alert('Mật khẩu WiFi nhà phải từ 8 ký tự');return false;}}
  return true;
}}
</script>
</body>
</html>"""


def wait_html() -> str:
    host = hostname()
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="25;url=/">
<meta name="theme-color" content="#070c10">
<title>Cozmars · Đang nối mạng</title>
<link rel="icon" type="image/svg+xml" href="/static/cozmars-logo.svg">
<link rel="stylesheet" href="/static/wifi.css">
</head>
<body>
<main class="wait">
  <img class="logo" src="/static/cozmars-logo.svg" width="72" height="72" alt="Cozmars">
  <h1>Đang áp dụng mạng…</h1>
  <div class="spinner" aria-hidden="true"></div>
  <p>Chờ khoảng 30 giây, rồi mở robot trên WiFi nhà:<br>
  <code>http://{host}.local/</code></p>
</main>
</body>
</html>"""


def attach_routes(app) -> None:
    from aiohttp import web

    async def wifi_get(_request: web.Request) -> web.Response:
        return web.Response(text=page_html(ssid=read_ssid()), content_type="text/html")

    async def save_wifi(request: web.Request) -> web.Response:
        try:
            data = await request.post()
        except Exception:
            data = {}
        ssid = str(data.get("ssid") or "")
        password = str(data.get("pass") or data.get("password") or "")
        try:
            save_credentials(ssid, password)
            return web.Response(text=page_html(ssid=ssid, saved=True), content_type="text/html")
        except Exception as exc:  # noqa: BLE001
            return web.Response(
                text=page_html(ssid=ssid, err=str(exc)),
                content_type="text/html",
                status=400,
            )

    async def restart_wifi(request: web.Request) -> web.Response:
        # Nếu form gửi kèm ssid/pass (nút Áp dụng) thì lưu trước
        try:
            data = await request.post()
            ssid = str(data.get("ssid") or "").strip()
            password = str(data.get("pass") or "").strip()
            if ssid and len(password) >= 8:
                try:
                    save_credentials(ssid, password)
                except Exception as exc:  # noqa: BLE001
                    return web.Response(
                        text=page_html(ssid=ssid, err=str(exc)),
                        content_type="text/html",
                        status=400,
                    )
        except Exception:
            pass

        async def _later() -> None:
            await asyncio.sleep(1.2)
            try:
                restart_network()
            except Exception as exc:  # noqa: BLE001
                print(f"[WIFI] restart fail — {exc}", flush=True)

        asyncio.create_task(_later())
        return web.Response(text=wait_html(), content_type="text/html")

    app.router.add_get("/wifi", wifi_get)
    app.router.add_get("/wifi/", wifi_get)
    app.router.add_route("*", "/save_wifi", save_wifi)
    app.router.add_route("*", "/restart_wifi", restart_wifi)


def _captive_allow(path: str) -> bool:
    return path.startswith(
        ("/wifi", "/save_wifi", "/restart_wifi", "/static", "/fw", "/about")
    )


def captive_middleware():
    """Khi đang hotspot: mọi request (Android/iOS captive check) → trang WiFi."""
    from aiohttp import web

    @web.middleware
    async def _mw(request: web.Request, handler):
        if not is_hotspot_mode():
            return await handler(request)
        path = request.path or "/"
        if _captive_allow(path):
            return await handler(request)
        # Probe captive / mọi trang khác → form WiFi
        raise web.HTTPFound("/wifi")

    return _mw


def attach_captive_catch_all(app) -> None:
    """Catch-all route (sau static) — phòng middleware không bắt hết."""
    from aiohttp import web

    async def _any(_request: web.Request) -> web.Response:
        if is_hotspot_mode():
            raise web.HTTPFound("/wifi")
        raise web.HTTPNotFound()

    app.router.add_route("*", "/{path_info:.*}", _any)


async def start_portal(host: str = "0.0.0.0", port: int = WIFI_PORT):
    """App riêng chỉ trang WiFi — luôn lắng nghe :8077."""
    try:
        from aiohttp import web
    except Exception as exc:  # noqa: BLE001
        print(f"[WIFI] MISS aiohttp — {exc}", flush=True)
        return None

    static_dir = Path(__file__).resolve().parent / "static"
    app = web.Application(middlewares=[captive_middleware()])

    async def root(_r):
        raise web.HTTPFound("/wifi")

    app.router.add_get("/", root)
    attach_routes(app)
    if static_dir.is_dir():
        app.router.add_static("/static", static_dir)
    attach_captive_catch_all(app)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, host, port)
        await site.start()
        print(f"[WIFI] portal http://{host}:{port}/  (LAN + hotspot mở, captive)", flush=True)
        return runner
    except OSError as exc:
        print(f"[WIFI] bind :{port} fail — {exc}", flush=True)
        await runner.cleanup()
        return None
