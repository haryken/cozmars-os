from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT = Path(__file__).resolve().parent.parent


def _home() -> Path:
    override = os.environ.get("COZMARS_HOME")
    if override:
        return Path(override)
    return Path.home() / ".cozmars"


def load() -> Tuple[Dict[str, Any], Dict[str, Any], Path]:
    home = _home()
    home.mkdir(parents=True, exist_ok=True)
    conf_src = ROOT / "config" / "conf.json"
    env_src = ROOT / "config" / "env.json"
    conf_dst = home / "conf.json"
    env_dst = home / "env.json"
    if not conf_dst.exists() and conf_src.exists():
        conf_dst.write_text(conf_src.read_text(encoding="utf-8"), encoding="utf-8")
    if not env_dst.exists() and env_src.exists():
        env_dst.write_text(env_src.read_text(encoding="utf-8"), encoding="utf-8")
    conf = json.loads(conf_dst.read_text(encoding="utf-8") if conf_dst.exists() else conf_src.read_text(encoding="utf-8"))
    env = json.loads(env_dst.read_text(encoding="utf-8") if env_dst.exists() else env_src.read_text(encoding="utf-8"))
    src_conf = json.loads(conf_src.read_text(encoding="utf-8")) if conf_src.exists() else {}
    src_env = json.loads(env_src.read_text(encoding="utf-8")) if env_src.exists() else {}
    if src_env.get("cliff_stop") and not env.get("cliff_stop"):
        env["cliff_stop"] = True
        save_env(env)
    if "sfx_mute" not in env:
        env["sfx_mute"] = ["Gazing_Scan"]
        save_env(env)
    if env.get("eye_color") in (None, "", "cyan"):
        env["eye_color"] = src_env.get("eye_color") or "TIP_OVER_TEAL"
        save_env(env)
    if src_conf.get("cliff") and not conf.get("cliff"):
        conf["cliff"] = src_conf["cliff"]
        conf_dst.write_text(json.dumps(conf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return conf, env, home


def save_env(env: Dict[str, Any]) -> None:
    home = _home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "env.json").write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
