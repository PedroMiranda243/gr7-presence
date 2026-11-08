"""Monta os cartões rotativos e o payload de atividade do Discord."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .detector import Target
from .gr7_state import PresetInfo
from .i18n import Translator, format_duration
from .stats import Summary

ACTIVITY_TYPES = {"playing": 0, "listening": 2, "watching": 3, "competing": 5}
STATUS_DISPLAY = {"name": 0, "state": 1, "details": 2}

CABINETS = {"Control Room", "Control Room Pro", "Matched Cabinet", "Matched Cabinet Pro", "Cabinet", "Cabinet Pro"}
MAX_EFFECTS_SHOWN = 3   # o resto vira "+N" (a cadeia completa fica no hover do ícone)

_GENRE_EMOJI = [
    ({"metal", "hard rock", "rock", "punk", "grunge", "stoner", "doom", "djent"}, "🤘"),
    ({"funk", "soul", "pop", "disco", "r&b"}, "🕺"),
    ({"blues", "jazz", "country"}, "🎷"),
    ({"ambient", "experimental", "cinematic", "electronic", "psychedelic"}, "🌌"),
]


@dataclass(frozen=True)
class Card:
    key: str
    details: str
    state: str
    small_image: str | None = None
    small_text: str | None = None


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def fit(text: str | None, limit: int = 128) -> str | None:
    """Respeita os limites do Discord (2 a `limit` caracteres UTF-16)."""
    if not text:
        return None
    text = " ".join(text.split())
    if _utf16_len(text) < 2:
        return None
    if _utf16_len(text) <= limit:
        return text
    while text and _utf16_len(text) > limit - 1:
        text = text[:-1]
    return text.rstrip(" ·,→-") + "…"


def _genre_emoji(tags: list[str]) -> str:
    lowered = [t.lower() for t in tags]
    for names, emoji in _GENRE_EMOJI:
        if any(name in tag for tag in lowered for name in names):   # "Funk & Soul" contém "funk"
            return emoji
    return "🎛️"


def _short_chain(effects: list[str]) -> str:
    shown = " → ".join(effects[:MAX_EFFECTS_SHOWN])
    rest = len(effects) - MAX_EFFECTS_SHOWN
    return f"{shown} +{rest}" if rest > 0 else shown


def build_cards(preset: PresetInfo | None, target: Target, summary: Summary | None,
                cfg, t: Translator, tracks: list[str] | None = None,
                rack_state: str | None = None, achievement: tuple[str, str] | None = None,
                level: str | None = None) -> list[Card]:
    """`rack_state`: "empty" (rack limpo) ou "scratch" (timbre montado depois de limpar o rack).
    `achievement`: (linha "🏆 Conquista: …", o que ela diz) enquanto vale o cartão de 24 h; `level`: a linha
    "Nível 7 · 1.060 pontos" (`achievement_view.card_bits`). As opções dizem se eles aparecem."""
    assets = cfg["assets"]
    plugin = target.kind == "plugin"
    if plugin:
        title = t("in_daw", host=target.host or "DAW")
        preset = None   # o estado do plugin fica salvo no projeto da DAW
    elif rack_state:
        title = t("rack_empty" if rack_state == "empty" else "scratch")
        preset = None   # o nome no topo do Guitar Rig ainda é do preset antigo
    elif preset and preset.name and cfg["show_preset"]:
        title = t("preset", name=preset.name)
    else:
        title = t("no_preset")
    cards: list[Card] = []

    if rack_state and not plugin:
        key = "rack_empty" if rack_state == "empty" else "scratch"
        cards.append(Card("rack", title, t(f"{key}_state"), assets["pedal"], t(f"{key}_hover")))

    if preset:
        effects = [c for c in preset.effects if c not in CABINETS]
        chain_hover = t("rack_hover", chain=" → ".join(preset.chain)) if preset.chain else None
        if preset.amp:
            line = t("amp_line", amp=preset.amp)
            if cfg["show_rack_chain"] and effects:
                line += " · " + _short_chain(effects)
            hover = chain_hover if cfg["show_rack_chain"] and chain_hover else t("amp_hover", amp=preset.amp)
            cards.append(Card("rig", title, line, assets["amp"], hover))
        elif cfg["show_rack_chain"] and effects:
            cards.append(Card("rig", title, "🎛️ " + _short_chain(effects), assets["pedal"], chain_hover))

        if cfg["show_tags"] and preset.tags:
            if preset.is_factory and preset.author:
                by = t("factory_by", author=preset.author)
            elif preset.author:
                by = t("user_preset_by", author=preset.author)
            else:
                by = t("user_preset")
            line = f"{_genre_emoji(preset.tags)} " + " · ".join(preset.tags[:4])
            cards.append(Card("style", title, line, assets["pedal"], by))

    if cfg["show_backing_track"] and tracks and not plugin:
        cards.append(Card("tape", t("backing_track"), " + ".join(tracks), assets["tape"], t("tape_hover")))

    if cfg["show_stats"] and summary is not None:
        parts = ["⏱ " + t("today", t=format_duration(summary.today))]
        if cfg["show_streak"] and summary.streak >= 2:
            parts.append(t("streak", n=summary.streak))
        else:
            parts.append(t("total", t=format_duration(summary.total)))
        if summary.sessions <= 1 and summary.total < 3600:
            hover = t("first_session")
        elif summary.sessions == 1:
            hover = t("stats_hover_one", t=format_duration(summary.total))
        else:
            hover = t("stats_hover", t=format_duration(summary.total), n=summary.sessions)
        if level and cfg["show_level"]:
            hover = f"{hover} · {level}"
        icon = assets["fire"] if cfg["show_streak"] and summary.streak >= 2 else assets["clock"]
        cards.append(Card("stats", title, " · ".join(parts), icon, hover))

    if achievement and cfg["show_achievement_card"]:
        line, says = achievement
        hover = level if level and cfg["show_level"] else says
        cards.append(Card("achievement", title, line, assets.get("trophy") or "trophy", hover))

    if not cards:
        state = "🎚️ VST3" if plugin else "🎛️ Guitar Rig 7"
        cards.append(Card("base", title, state, assets["daw"] if plugin else None, None))
    elif plugin:
        cards = [Card(c.key, c.details, c.state, c.small_image or assets["daw"], c.small_text) for c in cards]
    return cards


def build_activity(card: Card, target: Target, cfg, t: Translator, edition: str | None,
                   version: str | None, resolve: Callable[[str], str] = lambda key: key) -> dict:
    assets = {"large_image": resolve(cfg["assets"]["logo"])}
    large = t("large_text", edition=edition or "Guitar Rig 7", version=version) if version else (edition or "Guitar Rig 7")
    assets["large_text"] = fit(large)
    if card.small_image:
        assets["small_image"] = resolve(card.small_image)
        if fit(card.small_text):
            assets["small_text"] = fit(card.small_text)

    activity: dict = {
        "type": ACTIVITY_TYPES.get(cfg["activity_type"], 0),
        "status_display_type": STATUS_DISPLAY.get(cfg["status_display"], 0),
        "timestamps": {"start": int(target.started_at * 1000)},
        "assets": assets,
        "instance": False,
    }
    if fit(card.details):
        activity["details"] = fit(card.details)
    if fit(card.state):
        activity["state"] = fit(card.state)

    buttons = []
    for b in cfg["buttons"] or []:
        label, url = fit((b or {}).get("label"), 32), ((b or {}).get("url") or "").strip()
        if label and url.startswith(("https://", "http://")) and len(url) <= 512:
            buttons.append({"label": label, "url": url})
    if buttons:
        activity["buttons"] = buttons[:2]
    return activity
