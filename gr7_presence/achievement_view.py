"""O que se mostra de uma conquista fora do cálculo: o nome com o nível, os números, a cor da medalha e
as frases do aviso da bandeja, do cartão do Discord e do destaque no Painel.

Fica num lugar só para o loop (que avisa e monta o cartão, em outra thread) e as telas usarem as
mesmas frases. Não desenha nem fala com o Discord.
"""
from __future__ import annotations

import math
from datetime import date

from . import ui_kit as K
from .achievements import BY_KEY, Result, Unlock, musician_level, total_points
from .i18n import Translator, format_time

UNIT_ONE = ("weekends", "full_months", "goal_weeks", "own")   # o primeiro nível é 1: "1 mês", não "1 meses"
TIME_FAMILIES = ("marathon", "long_day", "loyal", "daw", "backing")   # o valor vira "3 h 24 min"
NOTE_NAMES = 3             # no aviso de várias conquistas, os nomes das 3 primeiras e "mais N"


def medal_colors(key: str, level: int) -> tuple[str, str, str] | None:
    """As cores da medalha de `key` no nível `level` (0 = apagada)."""
    d = BY_KEY[key]
    if level <= 0:
        return None
    if d.levels:
        return K.MEDAL_LEVELS[level - 1]
    return K.MEDAL_SECRET if d.secret else K.MEDAL_SINGLE


def level_name(key: str, level: int, t: Translator) -> str:
    """"Ouro" numa família; "Única" ou "Secreta" nas outras."""
    d = BY_KEY[key]
    if d.levels:
        return t(f"ach_level_{level}")
    return t("ach_secret") if d.secret else t("ach_single")


def mark_title(u: Unlock, t: Translator) -> str:
    """"Maratona · Ouro" numa família, só o nome nas outras (linha do tempo, destaque do Painel)."""
    name = t(f"ach_{u.key}")
    return f"{name} · {t(f'ach_level_{u.level}')}" if BY_KEY[u.key].levels else name


def mark_label(u: Unlock, t: Translator) -> str:
    """"Maratona (Ouro)" numa família, só o nome nas outras (aviso e cartão do Discord)."""
    name = t(f"ach_{u.key}")
    return f"{name} ({t(f'ach_level_{u.level}')})" if BY_KEY[u.key].levels else name


def short_date(d: date, t: Translator) -> str:
    return t("date_short", d=d.day, m=d.month)


def number(value: float, t: Translator) -> str:
    """88 · 6,8 · 3: inteiro a partir de 10, uma casa abaixo disso, sempre para baixo (para nunca mostrar
    "100 de 100" antes de chegar lá)."""
    if value >= 10:
        return str(int(value + 1e-9))
    v = math.floor(value * 10 + 1e-9) / 10
    return str(int(v)) if v.is_integer() else f"{v:.1f}".replace(".", t("decimal_sep"))


def unit(key: str, amount: float, t: Translator) -> str:
    """A unidade de uma família, no singular quando a quantidade é 1."""
    return t(f"ach_{key}_unit_one" if amount == 1 and key in UNIT_ONE else f"ach_{key}_unit")


def thousands(n: int, t: Translator) -> str:
    return f"{n:,}".replace(",", t("thousands_sep"))


def what(key: str, results: dict[str, Result], t: Translator) -> str:
    """O que a conquista diz: "Sua maior sessão: 3 h 24 min" numa família (com o valor de hoje) ou o que
    fazer numa única ou secreta ("Tocar entre 0 h e 5 h")."""
    d = BY_KEY[key]
    if not d.levels:
        return t(f"ach_{key}_desc")
    r = results.get(key)
    value = r.value if r else 0.0
    if key in TIME_FAMILIES:
        return t(f"ach_{key}_what", t=format_time(value * 3600, long=True))
    n = int(value + 1e-9)
    return t(f"ach_{key}_what_one" if n == 1 and key in UNIT_ONE else f"ach_{key}_what", n=thousands(n, t))


def level_line(results: list[Result], t: Translator) -> str:
    """"Nível 7 · 1.060 pontos": o nível de músico, para o cartão do Discord."""
    points = total_points(results)
    return t("ach_level_line", n=musician_level(points)[0], points=thousands(points, t))


def best_per_key(unlocks: list[Unlock]) -> list[Unlock]:
    """Duas marcas da mesma família de uma vez (Bronze e Prata na mesma sessão): fica a mais alta."""
    best: dict[str, Unlock] = {}
    for u in unlocks:
        if u.key not in best or u.level > best[u.key].level:
            best[u.key] = u
    return sorted(best.values(), key=lambda u: (u.got, u.points), reverse=True)


def note(unlocks: list[Unlock], results: list[Result], t: Translator) -> tuple[str, str] | None:
    """(título, texto) do aviso da bandeja: um por conquista ou um só para várias de uma vez."""
    items = best_per_key(unlocks)
    if not items:
        return None
    by_key = {r.key: r for r in results}
    level = musician_level(total_points(results))[0]
    if len(items) == 1:
        u = items[0]
        return (t("ach_note_title", name=mark_label(u, t)),
                t("ach_note_body", what=what(u.key, by_key, t), points=u.points, level=level))
    names = [mark_label(u, t) for u in items[:NOTE_NAMES]]
    rest = len(items) - len(names)
    if rest:
        names.append(t("ach_note_more", n=rest))
    joined = ", ".join(names[:-1]) + f" {t('list_and')} " + names[-1]
    return t("ach_note_many_title", n=len(items)), t("ach_note_many_body", names=joined)


def first_note(count: int, results: list[Result], t: Translator) -> tuple[str, str]:
    """O aviso único da primeira vez depois de atualizar: quantas marcas o histórico já tinha."""
    level = musician_level(total_points(results))[0]
    return t("ach_note_first_title"), t("ach_note_first_body", n=count, level=level)


def card_bits(card: Unlock | None, results: list[Result], t: Translator) -> tuple[tuple[str, str] | None, str]:
    """Para o Discord: ((linha "🏆 Conquista: Maratona (Ouro)", o que ela diz) ou None, a linha do nível).
    O `presence.build_cards` decide, pelas opções, se o cartão entra e se o nível aparece."""
    level = level_line(results, t)
    if card is None:
        return None, level
    return (t("ach_card", name=mark_label(card, t)), what(card.key, {r.key: r for r in results}, t)), level
