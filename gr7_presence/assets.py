"""Imagens do Rich Presence: chaves do Developer Portal, com plano B por URL do CDN.

O app do Discord guarda em cache a lista de imagens de cada aplicativo. Se esse cache estiver
velho (ex.: imagens enviadas depois do primeiro uso), as chaves não resolvem e o perfil fica sem
imagem. Nesse caso a resposta do SET_ACTIVITY volta sem "large_image"/"small_image", e passamos a
mandar o link público da imagem, que o Discord aceita via mp:external.
"""
from __future__ import annotations

import json
import logging
import urllib.request

log = logging.getLogger(__name__)

API = "https://discord.com/api/v10/oauth2/applications/{app}/assets"
CDN = "https://cdn.discordapp.com/app-assets/{app}/{asset}.png"


class AssetResolver:
    def __init__(self, client_id: str):
        self.client_id = str(client_id).strip()
        self.use_urls = False
        self._ids: dict[str, str] | None = None

    def reset(self) -> None:
        """Nova conexão com o Discord: volta a tentar as chaves."""
        self.use_urls = False

    def resolve(self, key: str) -> str:
        if self.use_urls and self._ids and key in self._ids:
            return CDN.format(app=self.client_id, asset=self._ids[key])
        return key

    def needs_fallback(self, sent: dict, echo: dict) -> bool:
        """True quando o Discord ignorou uma imagem e o plano B foi ligado (reenviar a atividade)."""
        missing = [k for k in ("large_image", "small_image") if sent.get(k) and not echo.get(k)]
        if not missing or self.use_urls:
            return False
        if self._ids is None:
            self._ids = self._fetch()
        if not self._ids:
            return False
        self.use_urls = True
        log.warning("O Discord não reconheceu %s; usando os links das imagens", ", ".join(missing))
        return True

    def _fetch(self) -> dict[str, str]:
        req = urllib.request.Request(API.format(app=self.client_id), headers={"User-Agent": "GR7Presence/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {a["name"]: a["id"] for a in json.load(resp)}
        except (OSError, ValueError, KeyError) as exc:
            log.warning("Não consegui buscar a lista de imagens do app: %s", exc)
            return {}
