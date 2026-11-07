---
version: 1
slug: "gr7-presence-main-window-py"
primary_target: "gr7_presence/main_window.py"
related_targets: []
---

# Janela principal do GR7 Presence

Modo: Operate. Quem abre: músico, entre uma música e outra, com o Guitar Rig 7 e o Discord abertos.
Tarefa: ver num relance o que o perfil mostra, se Discord e Guitar Rig estão conectados, quanto falta
para a meta do dia; mudar uma opção e ver o cartão mudar. Plataforma: Windows, Tkinter com imagens do
Pillow, sem dependência nova; tudo escala com o DPI. Uma janela só, com Painel, Estatísticas e Ajustes.

## Direction contract

THESIS: Palco. O que está ao vivo recebe a luz: o preset que está no perfil, a barra de hoje, a ação
principal. O resto fica na penumbra. Recusa o painel escuro de blocos iguais.

OWN-WORLD: palco azul-quase-preto (#0B0C10, #11131A, #14161D), luz quente de cima em degradê âmbar
#FFB347 para vermelho #FF5A36, vermelho da marca #E0141C só no amplificador. Títulos e números grandes
em Archivo Expanded 800; texto em Segoe UI. Painéis com cantos de 16 a 18 px, cadeia do rack em pílulas.

STORY: a pessoa entende o que o perfil mostra agora e o que falta para a meta, e muda o que aparece
sem editar arquivo.

FIRST VIEWPORT: trilho à esquerda (Painel, Estatísticas, Ajustes; atualização embaixo). Palco no topo:
nome do preset enorme à esquerda, pílulas da cadeia, status ao vivo e pausar; prévia do cartão do
Discord à direita com o rodízio. Abaixo, Meta de hoje e Conexões.

FORM: candidata 1 da lista própria (palco), fixada pelo dono do projeto. seed:2fff3fc64ee1dba6

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
