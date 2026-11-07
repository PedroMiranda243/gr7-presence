"""Loop principal: detecta o Guitar Rig 7, atualiza as estatísticas e o Discord."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Callable

from .config import DATA_DIR, Config
from .assets import AssetResolver
from .detector import Detector, Target, file_version
from .discord_ipc import DiscordError, DiscordIPC
from .gr7_state import PresetInfo, PresetReader
from .i18n import Translator, format_time
from .live import LivePresetReader, loaded_tracks
from .preset_library import PresetLibrary
from .presence import build_activity, build_cards
from .stats import Stats
from .updates import Release, UpdateChecker

log = logging.getLogger(__name__)

TICK_SECONDS = 5.0
RETRY_SECONDS = 15.0
MIN_ROTATE_SECONDS = 15.0
DEFAULT_EXE = r"C:\Program Files\Native Instruments\Guitar Rig 7\Guitar Rig 7.exe"


class PresenceApp:
    def __init__(self, config: Config, stats: Stats, reader: PresetReader | None = None,
                 library: PresetLibrary | None = None, live_state_path: Path = DATA_DIR / "live_state.json",
                 updates: UpdateChecker | None = None):
        self.config = config
        self.updates = updates or UpdateChecker()
        self.on_update: Callable[[Release], None] | None = None
        self.live_state_path = Path(live_state_path)
        self.stats = stats
        self.reader = reader or PresetReader()
        self.library = library or PresetLibrary()
        self.live = LivePresetReader(self.library)
        self.assets = AssetResolver(config["client_id"])
        self.t = Translator(config["language"])
        self.detector = Detector(config["detect_plugin_hosts"])
        self.ipc: DiscordIPC | None = None
        self.paused = False
        self.status_text = self.t("tray_waiting")
        self.active = False
        self.on_status: Callable[[str, bool], None] | None = None
        self.on_note: Callable[[str, str], None] | None = None    # notificação do Windows (título, texto)
        # O que o loop viu na última volta (preset, alvo, faixas, estado do rack), para a prévia dos
        # Ajustes mostrar o cartão de verdade. None com o Guitar Rig fechado.
        self.last_state: tuple | None = None
        self._goal_day: date | None = None
        self._goal_before = 0.0
        # Para o Painel: o cartão que está no perfil agora (atividade, posição, total, quando foi) e o
        # estado da leitura da tela: "reading", "minimized", "no_ocr" ou None (sem Guitar Rig ou plugin).
        self.showing: dict | None = None
        self.screen: str | None = None
        self.pause_until: float | None = None
        self._minimized_noted: tuple | None = None

        self._stop = threading.Event()
        self._target: Target | None = None
        self._card_index = 0
        self._last_sent = 0.0
        self._last_activity: dict | None = None
        self._last_connect_try = 0.0
        self._last_signature: tuple | None = None
        self._versions: dict[str, str | None] = {}
        self._live_name: str | None = None
        self._cleared = False             # rack limpo desde que este preset apareceu na tela
        self._rack_empty = False          # última medição da área do rack

    # ---- ciclo de vida -------------------------------------------------------------------
    def run(self) -> None:
        log.info("GR7 Presence iniciado")
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                log.exception("Erro no loop principal")
            self._stop.wait(TICK_SECONDS)
        self._shutdown()

    def stop(self) -> None:
        self._stop.set()

    def _shutdown(self) -> None:
        if self._target:
            self.stats.end()
            self._target = None
        if self.ipc:
            self.ipc.clear_activity()
            self.ipc.close()
        log.info("GR7 Presence encerrado")

    def set_paused(self, paused: bool, seconds: float | None = None) -> None:
        """Pausa (até a pessoa voltar, ou por `seconds`) ou retoma a presença."""
        self.paused = paused
        self.pause_until = time.time() + seconds if paused and seconds else None
        self._last_activity = None
        log.info("Presença %s%s", "pausada" if paused else "retomada", f" por {seconds:.0f} s" if paused and seconds else "")

    @property
    def discord_connected(self) -> bool:
        return bool(self.ipc and self.ipc.connected)

    # ---- um passo do loop ----------------------------------------------------------------
    def tick(self) -> None:
        if self.paused and self.pause_until and time.time() >= self.pause_until:
            self.set_paused(False)   # acabou a pausa de 1 hora
        if self.config.reload_if_changed():
            self.t = Translator(self.config["language"])
            self.detector.detect_plugins = bool(self.config["detect_plugin_hosts"])
            self._last_activity = None
            if self.ipc and self.ipc.client_id != str(self.config["client_id"]).strip():
                self.ipc.close()
                self.ipc = None
                self.assets = AssetResolver(self.config["client_id"])
        self._check_updates()

        target = self.detector.find()
        if not _same_target(target, self._target):
            if self._target:
                self.stats.end()
                self._clear()
            if target:
                self.stats.start(target.started_at, target.kind, target.host)
            self._target = target
            self._card_index = 0
            self._last_sent = 0.0
            self._last_signature = None
            self._live_name, self._cleared = self._recall_live(target) if target else (None, False)
            self._rack_empty = self._cleared

        if not target:
            self.last_state = None
            self.screen = None
            self._set_status(self.t("tray_waiting"), False)
            self._keepalive()
            return

        preset, tracks, rack_state = self._current_state(target)
        if rack_state:   # rack vazio/montado na hora: não conta tempo para o preset antigo
            self.stats.tick(None, None)
        else:
            self.stats.tick(preset.name if preset else None, preset.amp if preset else None)
        self.stats.save_if_due()
        self.last_state = (preset, target, tracks, rack_state)
        self._check_goal()
        self._check_minimized(target, preset)

        if self.paused:
            self._clear()
            self._set_status(self.t("tray_paused"), False)
            return
        if not str(self.config["client_id"]).strip():
            self._set_status(self.t("tray_no_client"), False)
            return
        if not self._ensure_connected():
            self.showing = None   # o Discord está fechado: nada no perfil
            return

        self._update_discord(target, preset, tracks, rack_state)

    # ---- partes do passo -----------------------------------------------------------------
    def _check_updates(self) -> None:
        if self.config["check_updates"] and self.updates.due():
            self.updates.check_in_background(self._update_found)

    def _check_goal(self, today: date | None = None) -> None:
        """Avisa uma vez quando o tempo de hoje passa da meta. Só conta a virada que acontece com o
        programa aberto: abrir o programa já acima da meta não avisa de novo."""
        try:
            goal = int(self.config["daily_goal_minutes"] or 0) * 60
        except (TypeError, ValueError):
            goal = 0
        today = today or date.today()
        seconds = self.stats.seconds_on(today)
        crossed = self._goal_day == today and self._goal_before < goal <= seconds
        self._goal_day, self._goal_before = today, seconds
        if not (crossed and goal and self.config["notify_goal"] and self.on_note):
            return
        body = self.t("goal_note_body", t=format_time(goal))
        streak = self.stats.summary(today=today).streak
        if streak >= 1:
            body += " " + self.t("goal_note_streak", n=streak + 1)
        try:
            self.on_note(self.t("goal_note_title"), body)
        except Exception:
            log.exception("Falha ao avisar da meta")

    def _check_minimized(self, target: Target, preset: PresetInfo | None) -> None:
        """Estado da leitura da tela para o Painel e, uma vez por abertura do Guitar Rig, o aviso de
        que ele foi minimizado: minimizado, ele não desenha a janela e o perfil para no último preset."""
        if target.kind != "standalone":
            self.screen = None
            return
        if self.live.minimized:
            self.screen = "minimized"
        else:
            self.screen = "reading" if self.live.ocr.available else "no_ocr"
        run = (target.pid, target.started_at)
        if self.screen != "minimized" or self._minimized_noted == run:
            return
        self._minimized_noted = run
        if not (self.config["notify_minimized"] and self.on_note):
            return
        name = preset.name if preset and preset.name else None
        body = self.t("min_note_body", name=name) if name else self.t("min_note_body_noname")
        try:
            self.on_note(self.t("min_note_title"), body)
        except Exception:
            log.exception("Falha ao avisar que o Guitar Rig foi minimizado")

    def _update_found(self, release: Release) -> None:
        if self.on_update:
            try:
                self.on_update(release)
            except Exception:
                log.exception("Falha ao avisar da versão nova")

    def _current_state(self, target: Target) -> tuple[PresetInfo | None, list[str], str | None]:
        """Preset atual, faixas abertas no Tape Deck e estado do rack ("empty", "scratch" ou None)."""
        if target.kind != "standalone":
            return None, [], None
        saved = self.reader.read()                # como o GR7 estava ao fechar (ele reabre assim)
        reading = self.live.read(target.pid)      # o que aparece na janela agora
        live = reading.name if reading else None
        before = (self._live_name, self._cleared)
        if live and live != self._live_name:
            log.info("Preset na tela: %s", live)
            self._cleared = False                 # outro preset carregado: o rack voltou a ser dele
        self._live_name = live or self._live_name  # janela minimizada: mantém o último lido
        if reading and reading.rack_empty is not None:
            self._rack_empty = reading.rack_empty
            if reading.rack_empty and not self._cleared:
                # "Clear Rack" mantém o nome do preset no topo; daqui em diante, até outro preset
                # ser carregado, o que estiver no rack é um timbre montado na hora.
                log.info("Rack vazio (o topo ainda mostra %s)", self._live_name)
                self._cleared = True
        if self._live_name and (self._live_name, self._cleared) != before:
            self._remember_live(target, self._live_name, self._cleared)
        rack_state = ("empty" if self._rack_empty else "scratch") if self._cleared else None
        preset = saved
        name = self._live_name
        if name and (saved is None or name.lower() != (saved.name or "").lower()):
            # O LastEditBuffer é do preset antigo; os detalhes vêm do arquivo .ngrr do preset novo.
            preset = self.library.load(name) or PresetInfo(name=name)
            if saved and saved.edition and not preset.edition:
                preset = replace(preset, edition=saved.edition)
        return preset, loaded_tracks(target.pid), rack_state

    def _remember_live(self, target: Target, name: str, cleared: bool = False) -> None:
        """Guarda o último preset lido da tela, para não voltar ao LastEditBuffer (velho) se este
        programa reiniciar com o Guitar Rig minimizado."""
        data = {"pid": target.pid, "started_at": target.started_at, "preset": name, "cleared": cleared}
        try:
            self.live_state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.live_state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.live_state_path)
        except OSError as exc:
            log.debug("Não consegui salvar %s: %s", self.live_state_path, exc)

    def _recall_live(self, target: Target) -> tuple[str | None, bool]:
        """Preset lido antes (e se o rack tinha sido limpo), desde que seja da mesma execução do
        Guitar Rig."""
        try:
            data = json.loads(self.live_state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None, False
        same_run = data.get("pid") == target.pid and abs(data.get("started_at", 0) - target.started_at) < 2
        if same_run and data.get("preset"):
            log.info("Preset lembrado desta sessão do Guitar Rig: %s", data["preset"])
            return data["preset"], bool(data.get("cleared"))
        return None, False

    def _ensure_connected(self) -> bool:
        if self.ipc and self.ipc.connected:
            try:
                self.ipc.poll()
                return True
            except DiscordError as exc:
                log.warning("Discord desconectou: %s", exc)
        now = time.time()
        if now - self._last_connect_try < RETRY_SECONDS:
            self._set_status(self.t("tray_no_discord"), False)
            return False
        self._last_connect_try = now
        self.ipc = DiscordIPC(self.config["client_id"])
        try:
            self.ipc.connect()
        except DiscordError as exc:
            log.info("Sem Discord: %s", exc)
            self._set_status(self.t("tray_no_discord"), False)
            return False
        self._last_activity = None
        self.assets.reset()
        return True

    def _update_discord(self, target: Target, preset: PresetInfo | None, tracks: list[str],
                        rack_state: str | None = None) -> None:
        now = time.time()
        summary = self.stats.summary() if self.config["show_stats"] else None
        cards = build_cards(preset, target, summary, self.config, self.t, tracks, rack_state)

        signature = ((preset.name, preset.amp, tuple(preset.chain)) if preset else (target.kind, target.host),
                     tuple(tracks), rack_state)
        preset_changed = self._last_signature is not None and signature != self._last_signature
        self._last_signature = signature

        rotate = max(MIN_ROTATE_SECONDS, float(self.config["rotate_seconds"] or 20))
        if preset_changed:
            self._card_index = 0
        elif self._last_activity is not None and now - self._last_sent >= rotate:
            self._card_index += 1
        elif self._last_activity is not None:
            return   # ainda é a vez do cartão atual
        card = cards[self._card_index % len(cards)]

        edition = (preset.edition if preset and preset.edition else None) or "Guitar Rig 7"
        if target.kind == "plugin":
            edition = "Guitar Rig 7 (VST3)"
        version = self._version(target.exe or DEFAULT_EXE)
        activity = build_activity(card, target, self.config, self.t, edition, version, self.assets.resolve)

        showing = {"activity": activity, "index": self._card_index % len(cards), "count": len(cards), "sent_at": now,
                   "rotate": rotate}
        if activity == self._last_activity:
            self._last_sent = now
            self.showing = showing
            return
        try:
            response = self.ipc.set_activity(activity)
            echo = (response.get("data") or {}).get("assets") or {}
            if self.assets.needs_fallback(activity["assets"], echo):
                activity = build_activity(card, target, self.config, self.t, edition, version, self.assets.resolve)
                self.ipc.set_activity(activity)
        except DiscordError as exc:
            log.warning("Falha ao atualizar o Discord: %s", exc)
            self._set_status(self.t("tray_no_discord"), False)
            self.showing = None
            return
        log.debug("Cartão %s: %s | %s", card.key, activity.get("details"), activity.get("state"))
        self._last_activity = activity
        self._last_sent = now
        self.showing = showing | {"activity": activity}
        if rack_state:
            shown = self.t("rack_empty" if rack_state == "empty" else "scratch")
        else:
            shown = (preset.name if preset and preset.name else None) or target.host or "Guitar Rig 7"
        self._set_status(self.t("tray_playing", name=shown), True)

    def _clear(self) -> None:
        if self._last_activity is not None and self.ipc:
            self.ipc.clear_activity()
        self._last_activity = None
        self.showing = None

    def _keepalive(self) -> None:
        """Sem GR7 aberto, só responde PINGs; a conexão fica pronta para a próxima sessão."""
        if self.ipc and self.ipc.connected:
            try:
                self.ipc.poll()
            except DiscordError:
                pass

    def _version(self, exe: str) -> str | None:
        if exe not in self._versions:
            self._versions[exe] = file_version(exe) if Path(exe).exists() else None
        return self._versions[exe]

    def _set_status(self, text: str, active: bool) -> None:
        if text != self.status_text or active != self.active:
            self.status_text, self.active = text, active
            if self.on_status:
                try:
                    self.on_status(text, active)
                except Exception:
                    log.exception("Falha ao atualizar a bandeja")


def _same_target(a: Target | None, b: Target | None) -> bool:
    if a is None or b is None:
        return a is b
    return (a.kind, a.pid) == (b.kind, b.pid)
