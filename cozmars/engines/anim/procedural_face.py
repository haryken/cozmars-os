"""Vector ProceduralFace — 19 tham số mỗi mắt (anim JSON Cozmo/Vector)."""

from __future__ import annotations

# EyeCenterX/Y, ScaleX/Y, Angle, 8 corner radii, 6 lid params
N = 19

# WireOS anim_eyes_neutral: kéo IOD vào (~73px tâm-tâm, không để 92px nominal).
IDLE_L = [9.17, 0.0, 1.214, 0.905, 0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
IDLE_R = [-10.21, 0.0, 1.222, 0.905, 0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
DEFAULT = list(IDLE_L)


def _eye(base: list[float], *overrides: tuple[int, float]) -> list[float]:
    out = list(base)
    for i, v in overrides:
        out[i] = v
    return out


def _face(L: list[float], R: list[float], **extra: float) -> dict:
    return {
        "L": L,
        "R": R,
        "a": float(extra.get("a", 0)),
        "cx": float(extra.get("cx", 0)),
        "cy": float(extra.get("cy", 0)),
        "sx": float(extra.get("sx", 1)),
        "sy": float(extra.get("sy", 1)),
    }


# Canned expressions — cùng rig Vector idle, không đổi hue.
PRESETS: dict[str, dict] = {
    "neutral": _face(IDLE_L, IDLE_R),
    "happy": _face(_eye(IDLE_L, (16, 0.30)), _eye(IDLE_R, (16, 0.30))),
    "sad": _face(
        _eye(IDLE_L, (3, 0.82), (13, 0.10), (14, 11.0)),
        _eye(IDLE_R, (3, 0.82), (13, 0.10), (14, 11.0)),
    ),
    "angry": _face(
        _eye(IDLE_L, (1, 1.41), (3, 0.852), (5, 0.60), (6, 0.60), (11, 0.60), (12, 0.60), (13, 0.55), (14, 7.5)),
        _eye(IDLE_R, (5, 0.60), (6, 0.60), (11, 0.60), (12, 0.60), (13, 0.55), (14, 7.5)),
    ),
    "surprised": _face(
        _eye(IDLE_L, (5, 0.668), (6, 0.668), (9, 0.891), (10, 0.703), (11, 0.668), (12, 0.668)),
        _eye(IDLE_R, (5, 0.668), (6, 0.668), (9, 0.891), (10, 0.703), (11, 0.668), (12, 0.668)),
        sx=1.357,
        sy=1.507,
        cy=-8.06,
    ),
    "focused": _face(
        _eye(IDLE_L, (3, 0.62), (13, 0.22), (16, 0.20)),
        _eye(IDLE_R, (3, 0.62), (13, 0.22), (16, 0.20)),
    ),
    "sleepy": _face(
        _eye(IDLE_L, (3, 0.77), (13, 0.52), (16, 0.08)),
        _eye(IDLE_R, (3, 0.77), (13, 0.52), (16, 0.08)),
    ),
    "auto": _face(IDLE_L, IDLE_R),
}


def named(name: str) -> dict:
    exp = name if name in PRESETS else "neutral"
    face = dict(PRESETS.get(exp) or PRESETS["neutral"])
    face["name"] = exp
    face["L"] = list(face["L"])
    face["R"] = list(face["R"])
    return face


def from_keyframe(kf: dict) -> dict:
    def _one(src) -> list[float]:
        vals = [round(float(x), 3) for x in (src or [])[:N]]
        if len(vals) < N:
            vals.extend(DEFAULT[len(vals) :])
        return vals

    return {
        "L": _one(kf.get("leftEye") or kf.get("L")),
        "R": _one(kf.get("rightEye") or kf.get("R")),
        "a": round(float(kf.get("faceAngle") or kf.get("a") or 0), 3),
        "cx": round(float(kf.get("faceCenterX") or kf.get("cx") or 0), 3),
        "cy": round(float(kf.get("faceCenterY") or kf.get("cy") or 0), 3),
        "sx": round(float(kf.get("faceScaleX") or kf.get("sx") or 1), 3),
        "sy": round(float(kf.get("faceScaleY") or kf.get("sy") or 1), 3),
    }
