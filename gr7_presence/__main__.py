"""python -m gr7_presence [--console] [--debug] [--preview] [--autostart on|off]"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
from logging.handlers import RotatingFileHandler

from .config import DATA_DIR, LOG_PATH, STATS_PATH, Config


def _setup_logging(debug: bool, console: bool) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [RotatingFileHandler(LOG_PATH, maxBytes=512_000, backupCount=2, encoding="utf-8")]
    if console and sys.stdout:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    for noisy in ("asyncio", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _preview(config: Config) -> int:
    """Mostra os cartões que iriam para o Discord, sem conectar."""
    import time

    from .detector import Target
    from .gr7_state import PresetReader
    from .i18n import Translator
    from .presence import build_activity, build_cards
    from .stats import Stats

    t = Translator(config["language"])
    preset = PresetReader().read()
    target = Target("standalone", 0, time.time() - 3600)
    summary = Stats(STATS_PATH).summary()
    for card in build_cards(preset, target, summary, config, t):
        activity = build_activity(card, target, config, t, preset.edition if preset else None, "7.0.2")
        print(json.dumps(activity, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gr7_presence", description="Discord Rich Presence para o Guitar Rig 7")
    parser.add_argument("--console", action="store_true", help="roda sem bandeja, com log no terminal")
    parser.add_argument("--debug", action="store_true", help="log detalhado")
    parser.add_argument("--preview", action="store_true", help="mostra os cartões e sai")
    parser.add_argument("--autostart", choices=["on", "off"], help="liga/desliga o início com o Windows e sai")
    args = parser.parse_args(argv)

    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _setup_logging(args.debug, args.console or args.preview)
    from .app_icon import set_app_id
    from .live import set_dpi_aware
    from .migrate import migrate
    set_dpi_aware()
    set_app_id()   # antes de qualquer janela: senão a barra de tarefas mostra o ícone do Python
    migrate()
    config = Config()

    if args.preview:
        return _preview(config)
    if args.autostart:
        from . import autostart
        autostart.set_enabled(args.autostart == "on")
        print("Início com o Windows:", "ligado" if autostart.is_enabled() else "desligado")
        return 0

    from .single_instance import SingleInstance
    lock = SingleInstance("GR7PresenceSingleInstance")
    if not lock.acquired:
        logging.getLogger(__name__).info("Já existe uma cópia rodando; saindo")
        return 0

    from .app import PresenceApp
    from .stats import Stats

    app = PresenceApp(config, Stats(STATS_PATH))
    if args.console:
        try:
            app.run()
        except KeyboardInterrupt:
            app.stop()
            app._shutdown()
        return 0

    from .tray import TrayUI
    worker = threading.Thread(target=app.run, name="presence", daemon=True)
    worker.start()
    TrayUI(app).run()          # bloqueia até "Sair"
    app.stop()
    worker.join(timeout=10)
    return 0


if __name__ == "__main__":
    sys.exit(main())
