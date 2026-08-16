"""JdocSettings API — cùng path WireOS /api/mods/JdocSettings/*."""

from __future__ import annotations

from aiohttp import web

from cozmars.config import save_env
from cozmars.engines.anim import eye_color as eye_color_mod

EYE_PRESETS = [
    "TIP_OVER_TEAL",
    "OVERFIT_ORANGE",
    "UNCANNY_YELLOW",
    "NON_LINEAR_LIME",
    "SINGULARITY_SAPPHIRE",
    "FALSE_POSITIVE_PURPLE",
    "CONFUSION_MATRIX_GREEN",
    "RAINBOW_EYES",
    "ROBOT_RED",
]
VOL_PCT = (0, 20, 40, 60, 80, 100)


def _ok() -> web.Response:
    return web.json_response({"status": "ok"})


def _err(msg: str, code: int = 400) -> web.Response:
    return web.json_response({"status": "error", "message": msg}, status=code)


def _save(wired) -> None:
    try:
        save_env(wired.brain.env)
    except Exception:
        pass


async def handle(wired, request: web.Request, path: str) -> web.Response:
    env = wired.brain.env
    anim = wired.brain.anim
    q = request.query

    if path == "getLocation":
        return web.Response(text=str(env.get("location") or ""))
    if path == "setLocation":
        env["location"] = q.get("location", "")
        _save(wired)
        return _ok()
    if path == "getTimezone":
        return web.Response(text=str(env.get("timezone") or "Asia/Bangkok"))
    if path == "setTimezone":
        env["timezone"] = q.get("timezone") or "Asia/Bangkok"
        _save(wired)
        return _ok()
    if path == "getFahrenheit":
        return web.Response(text=str(env.get("temp_unit") or "c"))
    if path == "setFahrenheit":
        env["temp_unit"] = "f" if str(q.get("t") or "c").lower().startswith("f") else "c"
        _save(wired)
        return _ok()
    if path == "getVolume":
        pct = int(env.get("say_vol") or 80)
        level = min(range(6), key=lambda i: abs(VOL_PCT[i] - pct))
        return web.Response(text=str(level))
    if path == "setVolume":
        try:
            level = max(0, min(5, int(q.get("level", "3"))))
        except ValueError:
            return _err("bad level")
        pct = VOL_PCT[level]
        env["say_vol"] = pct
        anim.volume = pct / 100.0
        _save(wired)
        return _ok()
    if path == "getEyeColor":
        name = str(env.get("eye_color") or "TIP_OVER_TEAL")
        hue = env.get("eye_hue")
        sat = env.get("eye_sat")
        custom = name.upper() == "CUSTOM"
        preset = EYE_PRESETS.index(name) if name in EYE_PRESETS else 0
        body = {
            "iscustom": custom,
            "preset": None if custom else preset,
            "hue": None if hue is None else float(hue),
            "saturation": None if sat is None else float(sat),
        }
        return web.json_response(body)
    if path == "setEyeColor":
        try:
            preset = int(q.get("preset", "0"))
        except ValueError:
            return _err("bad preset")
        if not 0 <= preset < len(EYE_PRESETS):
            return _err("preset out of range")
        anim.set_eye_color(EYE_PRESETS[preset])
        return _ok()
    if path == "setCustomEyeColor":
        try:
            hue = float(q.get("hue", "0.5"))
            sat = float(q.get("saturation", "1"))
        except ValueError:
            return _err("bad hsv")
        anim.set_eye_color("CUSTOM", hue=hue, sat=sat)
        return _ok()
    if path == "setExpression":
        anim.set_expression(str(q.get("name") or "auto"))
        return _ok()
    if path == "getCliff":
        return web.Response(text="1" if env.get("cliff_stop", True) else "0")
    if path == "setCliff":
        env["cliff_stop"] = q.get("on", "1") not in ("0", "false", "off")
        _save(wired)
        return _ok()
    if path == "setStim":
        mode = str(q.get("mode") or "auto")
        if mode == "auto":
            wired.brain._stim_lock = None
        else:
            try:
                val = max(0.0, min(1.0, float(q.get("value", "0.5"))))
            except ValueError:
                return _err("bad stim")
            wired.brain._stim_lock = val
            wired.brain.mood.stimulated = val
        return _ok()
    return _err("404 not found", 404)
