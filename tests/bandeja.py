"""A bandeja de verdade nos testes, sem o erro intermitente do pystray.

O pystray registra a janela de cada ícone com um nome feito do endereço do objeto (`id`) e nunca
desfaz o registro. Se um ícone é jogado fora e o próximo nasce no mesmo endereço, o Windows recusa:
"a classe já existe" (WinError 1410). Depende de onde a memória cai, então falha só às vezes; na CI da
1.4.0 derrubou um teste da bandeja. Guardar os ícones até o fim da rodada impede o endereço de se
repetir. No programa há um ícone só, e o problema não acontece.
"""
from gr7_presence.tray import TrayUI

_ICONS: list = []


def keep(icon):
    """Guarda o ícone até o fim dos testes e o devolve."""
    _ICONS.append(icon)
    return icon


def tray_ui(app) -> TrayUI:
    """Uma TrayUI cujo ícone de verdade fica guardado, mesmo que o teste o troque por um Mock."""
    ui = TrayUI(app)
    keep(ui.icon)
    return ui
