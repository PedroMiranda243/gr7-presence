"""Textos em português e inglês."""
from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "pt": {
        "preset": "🎸 {name}",
        "no_preset": "🎸 Tocando guitarra",
        "backing_track": "🎶 Backing track",
        "in_daw": "🎛️ Guitar Rig 7 no {host}",
        "amp_line": "🔊 {amp}",
        "amp_hover": "Amp: {amp}",
        "rack_hover": "Rack: {chain}",
        "effects_count": "+{n} efeitos",
        "effect_count_one": "+1 efeito",
        "factory_by": "Preset de fábrica por {author}",
        "user_preset": "Preset próprio",
        "user_preset_by": "Preset por {author}",
        "tape_hover": "Faixa carregada no Tape Deck",
        "rack_empty": "🎛️ Rack vazio",
        "rack_empty_state": "🔧 Começando um timbre do zero",
        "rack_empty_hover": "Rack limpo no Guitar Rig",
        "scratch": "🎛️ Timbre próprio",
        "scratch_state": "🔧 Montando do zero",
        "scratch_hover": "Rack montado na hora, sem preset salvo",
        "today": "Hoje {t}",
        "total": "Total {t}",
        "streak": "🔥 {n} dias seguidos",
        "stats_hover": "{t} tocados em {n} sessões",
        "stats_hover_one": "{t} tocados em 1 sessão",
        "first_session": "Primeira sessão!",
        "large_text": "{edition} · v{version}",
        "tray_waiting": "Aguardando o Guitar Rig 7…",
        "tray_no_discord": "Discord não encontrado, tentando de novo…",
        "tray_playing": "No Discord: {name}",
        "tray_paused": "Presença pausada",
        "tray_no_client": "Falta o Application ID no config.json",
        "menu_pause": "Pausar presença",
        "menu_stats": "Estatísticas…",
        "menu_config": "Abrir configurações",
        "menu_logs": "Abrir pasta de dados",
        "menu_autostart": "Iniciar com o Windows",
        "menu_quit": "Sair",
        "menu_update": "⬆️ Baixar a versão {version}",
        "menu_version": "GR7 Presence {version}",
        "update_title": "Saiu a versão {version} do GR7 Presence",
        "update_body": "Clique com o botão direito no ícone e escolha \"Baixar a versão {version}\".",
        "stats_title": "GR7 Presence · Estatísticas",
        "stats_today": "Hoje",
        "stats_week": "Últimos 7 dias",
        "stats_total": "Total",
        "stats_sessions": "Sessões",
        "stats_streak": "Sequência",
        "stats_best_streak": "Recorde",
        "stats_days": "{n} dias",
        "stats_top_presets": "Presets mais tocados",
        "stats_top_amps": "Amplificadores mais usados",
        "stats_recent": "Sessões recentes",
        "stats_empty": "Nenhuma sessão ainda. Abra o Guitar Rig 7 e toque um pouco!",
        "stats_live": "agora",
    },
    "en": {
        "preset": "🎸 {name}",
        "no_preset": "🎸 Playing guitar",
        "backing_track": "🎶 Backing track",
        "in_daw": "🎛️ Guitar Rig 7 in {host}",
        "amp_line": "🔊 {amp}",
        "amp_hover": "Amp: {amp}",
        "rack_hover": "Rack: {chain}",
        "effects_count": "+{n} effects",
        "effect_count_one": "+1 effect",
        "factory_by": "Factory preset by {author}",
        "user_preset": "Custom preset",
        "user_preset_by": "Preset by {author}",
        "tape_hover": "Track loaded in the Tape Deck",
        "rack_empty": "🎛️ Empty rack",
        "rack_empty_state": "🔧 Starting a tone from scratch",
        "rack_empty_hover": "Rack cleared in Guitar Rig",
        "scratch": "🎛️ Custom tone",
        "scratch_state": "🔧 Building from scratch",
        "scratch_hover": "Rack built on the spot, no saved preset",
        "today": "Today {t}",
        "total": "Total {t}",
        "streak": "🔥 {n}-day streak",
        "stats_hover": "{t} played in {n} sessions",
        "stats_hover_one": "{t} played in 1 session",
        "first_session": "First session!",
        "large_text": "{edition} · v{version}",
        "tray_waiting": "Waiting for Guitar Rig 7…",
        "tray_no_discord": "Discord not found, retrying…",
        "tray_playing": "On Discord: {name}",
        "tray_paused": "Presence paused",
        "tray_no_client": "Application ID missing in config.json",
        "menu_pause": "Pause presence",
        "menu_stats": "Statistics…",
        "menu_config": "Open settings",
        "menu_logs": "Open data folder",
        "menu_autostart": "Start with Windows",
        "menu_quit": "Quit",
        "menu_update": "⬆️ Download version {version}",
        "menu_version": "GR7 Presence {version}",
        "update_title": "GR7 Presence {version} is out",
        "update_body": "Right-click the icon and choose \"Download version {version}\".",
        "stats_title": "GR7 Presence · Statistics",
        "stats_today": "Today",
        "stats_week": "Last 7 days",
        "stats_total": "Total",
        "stats_sessions": "Sessions",
        "stats_streak": "Streak",
        "stats_best_streak": "Best",
        "stats_days": "{n} days",
        "stats_top_presets": "Most played presets",
        "stats_top_amps": "Most used amps",
        "stats_recent": "Recent sessions",
        "stats_empty": "No sessions yet. Open Guitar Rig 7 and play a little!",
        "stats_live": "now",
    },
}


class Translator:
    def __init__(self, language: str = "pt"):
        self.language = language if language in STRINGS else "pt"

    def __call__(self, key: str, **kwargs) -> str:
        text = STRINGS[self.language].get(key) or STRINGS["pt"].get(key, key)
        return text.format(**kwargs) if kwargs else text


def format_duration(seconds: float) -> str:
    """3725 -> '1h02', 540 -> '9min', 30 -> '0min'."""
    minutes = int(seconds // 60)
    hours, minutes = divmod(minutes, 60)
    if hours >= 100:
        return f"{hours}h"
    if hours:
        return f"{hours}h{minutes:02d}"
    return f"{minutes}min"
