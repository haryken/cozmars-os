"""say / listen — Google TTS HTTP; sim phát loa máy."""

from __future__ import annotations

from . import google_tts


class Voice:
    def say(self, text: str, lang: str = "vi") -> None:
        print(f"[VOICE] say lang={lang}  {text[:80]!r}", flush=True)
        google_tts.say(text, lang)
