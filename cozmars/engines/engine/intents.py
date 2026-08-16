"""Map mọi intent_* trong user_intent_map.json → hành động Cozmars."""

from __future__ import annotations

import json
from pathlib import Path

_NAMES = json.loads((Path(__file__).with_name("user_intent_map.json")).read_text(encoding="utf-8"))

# Vector cloud_intent → Cozmars action
INTENT_TO_ACTION = {
    "intent_imperative_halt": "halt",
    "intent_global_stop": "halt",
    "intent_global_stop_extend": "halt",
    "intent_imperative_forward": "forward",
    "intent_explore_start": "explore",
    "intent_imperative_backup": "backup",
    "intent_imperative_turnleft": "turn_left",
    "intent_imperative_turnright": "turn_right",
    "intent_imperative_turnaround": "turn_around",
    "intent_imperative_come": "come",
    "intent_imperative_lookatme": "lookatme",
    "intent_imperative_lookoverthere": "lookoverthere",
    "intent_imperative_quiet": "quiet",
    "intent_imperative_shutup": "quiet",
    "intent_imperative_volumeup": "vol_up",
    "intent_imperative_volumedown": "vol_down",
    "intent_imperative_volumelevel_extend": "vol_set",
    "intent_greeting_hello": "hello",
    "intent_greeting_goodbye": "goodbye",
    "intent_greeting_goodmorning": "hello",
    "intent_greeting_goodnight": "sleep",
    "intent_imperative_praise": "happy",
    "intent_imperative_scold": "scold",
    "intent_imperative_love": "happy",
    "intent_imperative_apology": "sad",
    "intent_imperative_apologize": "sad",
    "intent_imperative_abuse": "sad",
    "intent_imperative_dance": "dance",
    "intent_imperative_sing": "sing",
    "intent_play_firetruck": "firetruck",
    "intent_play_fistbump": "fistbump",
    "intent_play_blackjack": "game_blackjack",
    "intent_blackjack_hit": "game_hit",
    "intent_blackjack_stand": "game_stand",
    "intent_blackjack_playagain": "game_blackjack",
    "intent_play_anygame": "game_random",
    "intent_play_anytrick": "dance",
    "intent_play_pickupcube": "pickup_cube",
    "intent_play_rollcube": "roll_cube",
    "intent_play_keepaway": "keepaway",
    "intent_play_popawheelie": "lookatme",
    "intent_imperative_findcube": "find_cube",
    "intent_imperative_fetchcube": "fetch_cube",
    "intent_system_sleep": "sleep",
    "intent_system_charger": "charger",
    "intent_system_noaudio": "quiet",
    "intent_photo_take_extend": "photo",
    "intent_clock_time": "say_time",
    "intent_weather_extend": "weather",
    "intent_status_feeling": "feeling",
    "intent_knowledge_promptquestion": "listen",
    "intent_imperative_affirmative": "yes",
    "intent_imperative_negative": "no",
    "intent_amazon_signin": "skip",
    "intent_amazon_signout": "skip",
    "intent_test_wire": "hello",
    "intent_names_ask": "hello",
    "intent_meet_victor": "hello",
    "intent_names_username_extend": "hello",
    "intent_message_recordmessage": "listen",
    "intent_message_recordmessage_extend": "listen",
    "intent_message_playmessage": "sing",
    "intent_message_playmessage_extend": "sing",
    "intent_clock_checktimer": "say_time",
    "intent_clock_settimer": "say_time",
    "intent_clock_settimer_extend": "say_time",
    "intent_global_delete_extend": "halt",
    "intent_knowledge_response_extend": "listen",
    "intent_knowledge_response_extend_bypass": "listen",
    "intent_knowledge_no_response": "sad",
}

# aliases from sim / UI
INTENT_TO_ACTION.update({
    "wander": "explore",
    "explore": "explore",
    "idle": "halt",
    "stop": "halt",
    "nod": "come",
    "lift": "fistbump",
    "firetruck": "firetruck",
    "dance": "dance",
})


def known_intents() -> list[str]:
    return list(_NAMES)


def dispatch(name: str) -> str:
    if name in INTENT_TO_ACTION:
        return INTENT_TO_ACTION[name]
    # strip extend
    base = name.replace("_extend", "")
    if base in INTENT_TO_ACTION:
        return INTENT_TO_ACTION[base]
    if name.startswith("intent_") and name in _NAMES:
        return "skip"
    return ""
