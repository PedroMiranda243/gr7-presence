---
name: GR7 Presence
description: Janela de bandeja para Windows que mostra e controla o que o perfil do Discord exibe do Guitar Rig 7, na direção "Palco".
colors:
  bg: "#0B0C10"
  rail: "#0F1117"
  rail-line: "#1B1E29"
  rail-on: "#1B1E2A"
  stage: "#11131A"
  panel: "#13151C"
  panel-line: "#1E2130"
  field: "#151821"
  field-line: "#262A37"
  selected: "#272B38"
  track: "#232734"
  bar: "#2B3040"
  grid: "#1A1D27"
  scroll-thumb: "#2A2F3D"
  switch-off: "#2A2F3D"
  btn: "#26282E"
  btn-line: "#2F3137"
  text: "#F3F1EC"
  text-soft: "#C9C4BB"
  text-lead: "#D2CCC2"
  muted: "#9EA3B0"
  faint: "#7A8094"
  icon-off: "#8C92A4"
  dim: "#5A6177"
  glow: "#FFF5EA"
  on-accent: "#1A0E08"
  on-accent-off: "#3A2E26"
  pill: "#1F2128"
  pill-line: "#26282F"
  pill-text: "#E7E3DB"
  btn-stage: "#24262C"
  btn-stage-line: "#2C2E34"
  empty-line: "#2E3342"
  badge-off: "#1C1F29"
  badge-icon: "#2A1206"
  ok-bg: "#122923"
  warn-bg: "#2A2416"
  selection: "#4A3A22"
  title-text: "#B9BDC8"
  amber: "#FFB347"
  orange: "#FF5A36"
  red: "#E0141C"
  green: "#3DDC97"
  bad: "#FF8A6A"
  focus-ring: "#3E3124"
  cal-1: "#4A2620"
  cal-2: "#8F3A22"
  cal-3: "#E0602B"
  card: "#1E2027"
  card-line: "#2B2D34"
  card-muted: "#B5BAC1"
  card-button: "#3A3D46"
typography:
  display-xl:
    fontFamily: "Archivo, Segoe UI Variable, Segoe UI"
    fontSize: "46px"
    fontWeight: 800
    lineHeight: 0.98
    fontVariation: "'wght' 800, 'wdth' 125"
  display-lg:
    fontFamily: "Archivo, Segoe UI Variable, Segoe UI"
    fontSize: "38px"
    fontWeight: 800
    lineHeight: 0.98
    fontVariation: "'wght' 800, 'wdth' 125"
  headline:
    fontFamily: "Archivo, Segoe UI Variable, Segoe UI"
    fontSize: "30px"
    fontWeight: 800
    lineHeight: 1
    fontVariation: "'wght' 800, 'wdth' 125"
  stat:
    fontFamily: "Archivo, Segoe UI Variable, Segoe UI"
    fontSize: "34px"
    fontWeight: 800
    lineHeight: 1
    fontVariation: "'wght' 800, 'wdth' 118"
  stat-sm:
    fontFamily: "Archivo, Segoe UI Variable, Segoe UI"
    fontSize: "24px"
    fontWeight: 800
    lineHeight: 1.05
    fontVariation: "'wght' 800, 'wdth' 118"
  title:
    fontFamily: "Archivo, Segoe UI Variable, Segoe UI"
    fontSize: "15px"
    fontWeight: 700
    lineHeight: 1.2
    fontVariation: "'wght' 700, 'wdth' 112"
  body-lead:
    fontFamily: "Segoe UI Variable Text, Segoe UI"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  body:
    fontFamily: "Segoe UI Variable Text, Segoe UI"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.3
  body-sm:
    fontFamily: "Segoe UI Variable Text, Segoe UI"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Segoe UI Variable Text, Segoe UI"
    fontSize: "13.5px"
    fontWeight: 600
    lineHeight: 1.3
  button:
    fontFamily: "Segoe UI Variable Text, Segoe UI"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.3
  button-primary:
    fontFamily: "Segoe UI Variable Text, Segoe UI"
    fontSize: "13.5px"
    fontWeight: 700
    lineHeight: 1.3
  caption:
    fontFamily: "Segoe UI Variable Text, Segoe UI"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.3
  micro:
    fontFamily: "Segoe UI Variable Text, Segoe UI"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.3
  rail-label:
    fontFamily: "Segoe UI Variable Text, Segoe UI"
    fontSize: "10.5px"
    fontWeight: 600
    lineHeight: 1
rounded:
  stage: "18px"
  panel: "16px"
  badge: "15px"
  rail-item: "12px"
  primary: "11px"
  control: "10px"
  card: "8px"
  menu-item: "6px"
  bar: "5px"
  cell: "3px"
  pill: "9999px"
spacing:
  pill-gap: "6px"
  gap: "14px"
  panel-top: "19px"
  page-top: "20px"
  panel-x: "21px"
  page-x: "24px"
  stage: "28px"
  control-h: "34px"
  primary-h: "38px"
  rail: "78px"
components:
  stage:
    backgroundColor: "{colors.stage}"
    rounded: "{rounded.stage}"
    padding: "28px"
  panel:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.panel}"
    padding: "19px 21px"
  button-primary:
    backgroundColor: "{colors.amber}"
    textColor: "{colors.on-accent}"
    typography: "{typography.button-primary}"
    rounded: "{rounded.primary}"
    height: "38px"
  button-secondary:
    backgroundColor: "{colors.btn}"
    textColor: "{colors.text}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "0 14px"
    height: "34px"
  input:
    backgroundColor: "{colors.field}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "34px"
  segmented-item-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.text}"
    rounded: "{rounded.card}"
  segmented-item:
    backgroundColor: "{colors.field}"
    textColor: "{colors.muted}"
    rounded: "{rounded.card}"
  rail-item-active:
    backgroundColor: "{colors.rail-on}"
    textColor: "{colors.text}"
    typography: "{typography.rail-label}"
    rounded: "{rounded.rail-item}"
    width: "64px"
  rail-item-hover:
    backgroundColor: "{colors.field}"
    textColor: "{colors.icon-off}"
    rounded: "{rounded.rail-item}"
  chain-pill:
    textColor: "{colors.text-soft}"
    rounded: "{rounded.pill}"
    padding: "6px 12px"
  chain-pill-amp:
    backgroundColor: "{colors.red}"
    textColor: "#FFFFFF"
    rounded: "{rounded.pill}"
    padding: "6px 12px"
  switch-off:
    backgroundColor: "{colors.switch-off}"
    rounded: "{rounded.primary}"
    width: "38px"
    height: "22px"
  discord-card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.card-muted}"
    rounded: "{rounded.card}"
    padding: "12px"
---

# Design System: GR7 Presence

## Overview

**Creative North Star: "Palco"**

O que está ao vivo recebe a luz; o resto fica na penumbra. A janela é um palco azul-quase-preto em
camadas, com uma luz quente que desce de cima (âmbar para laranja) só sobre o que importa agora: o
preset que está no perfil, a barra de hoje no gráfico, a ação principal. Fica ao lado do Guitar Rig e
do Discord, os dois escuros, e precisa conviver com eles sem se confundir com nenhum.

A densidade é de ferramenta, não de site: uma janela de 960 × 640 (mínimo 860 × 560) com trilho de
78 px à esquerda e páginas que rolam. Os títulos e os números grandes são da Archivo larga e pesada; o
resto é Segoe UI, discreto, no tamanho de leitura do Windows. Não há painéis iguais lado a lado
competindo: um palco iluminado no topo e painéis apagados embaixo.

Tudo é desenhado pelo Pillow em pixels lógicos e multiplicado pela escala do Windows (`Painter`); o
Tkinter só mostra a imagem num Canvas. Os tokens moram num lugar só: `gr7_presence/ui_kit.py`.

**Key Characteristics:**
- Palco escuro em camadas (fundo, trilho, palco, painel, campo), sem bordas fortes.
- Luz radial quente só no palco de cada página; degradê âmbar → laranja só no que está "aceso".
- Archivo 800 larga nos títulos e números; Segoe UI nos textos e controles.
- Vermelho da marca só no amplificador da cadeia e no ícone do pedal.
- Quase sem movimento: a imagem é trocada inteira; o Painel se redesenha a cada 1 s.

## Colors

Escuros frios em camadas, uma luz quente e um vermelho de marca guardado para um único papel.

### Primary
- **Âmbar de Palco** (amber): começo de todo degradê aceso (chave ligada, deslizante, barra da meta,
  barra de hoje, botão principal, conquista ganha); ícone da página atual no trilho; item marcado nas
  listas; o contorno do foco do teclado e do campo com foco.
- **Laranja de Ribalta** (orange): fim do degradê aceso; o ponto de "versão nova" no trilho; o ponto de
  "Discord desconectado"; a borda do campo com valor inválido.

### Secondary
- **Vermelho do Pedal** (red): só a pílula do amplificador na cadeia do rack (texto branco, 4,9:1). É a
  cor do ícone do programa (`tools/icone_pedal.py`); não vira cor de botão, de erro nem de destaque.
- **Verde Conectado** (green): pontos de estado "ligado" (Discord, Guitar Rig, leitura da tela), o
  status de membro na prévia e a sessão ao vivo nas Estatísticas.

### Tertiary
- **Brasa** (bad): texto de erro em palavras simples (link inválido, falha ao baixar). Não é vermelho
  de alarme; é um laranja claro que se lê sobre o painel (7,9:1).
- **Rampa do calendário** (grid, cal-1, cal-2, cal-3, amber): os cinco tons do calendário dos dias
  tocados, de nada tocado até mais de 75 minutos (`CAL_RAMP`).

### Neutral
- **Fundo do Palco** (bg): a janela, a barra de título (Windows 11) e o espaço entre painéis.
- **Trilho** (rail) com a linha **rail-line** à direita; **rail-on** é o item escolhido.
- **Palco** (stage): o painel iluminado do topo de cada página.
- **Painel** (panel) com contorno **panel-line**: os blocos de conteúdo; panel-line também separa as
  linhas dentro deles.
- **Campo** (field) com contorno **field-line**: campos de texto, de escolha, segmentado, lista de
  opções; field também é o hover dos itens do trilho.
- **selected**: segmento escolhido e item com o mouse na lista de opções.
- **track** / **bar** / **grid** / **scroll-thumb** / **switch-off**: trilhos de progresso, barras do
  gráfico fora de hoje, grade do gráfico, barra de rolagem e indicadores de cartão apagados, chave
  desligada.
- **btn** / **btn-line**: o botão secundário (branco a 8 % sobre o painel).
- **Texto** (text, 16:1 no painel), **text-lead** (o parágrafo sob o título do palco), **text-soft**
  (fatos e itens de lista), **muted** (dicas e explicações, 7,2:1), **faint** (eixos, contadores,
  texto de exemplo nos campos; 4,6:1 no painel, o mínimo do sistema para texto), **icon-off** (ícones e
  rótulos do trilho fora da página atual).
- **dim**: só ícones de conquista ainda não ganha e pontos de "fechado/esperando". Nunca texto.
- **Brilho** (glow): os nomes enormes do palco e os números de destaque; um branco quente, não puro.
- **on-accent**: texto sobre o degradê do botão principal (10,6:1 no âmbar, 6,1:1 no laranja);
  **on-accent-off**, o mesmo texto com o botão desabilitado.
- **pill** / **pill-line** / **pill-text**: as pílulas da cadeia sobre o palco. **btn-stage** /
  **btn-stage-line**: o botão secundário sobre o palco ou a página (Pausar, Mais tarde).
- **empty-line**: o tracejado do cartão vazio. **badge-off** / **badge-icon**: a conquista ainda não
  ganha e o ícone escuro sobre a ganha. **ok-bg** / **warn-bg**: o fundo dos sinais da primeira
  abertura. **selection**: texto selecionado nos campos. **title-text**: o título na barra de título.
- **card**, **card-line**, **card-muted**, **card-button**: só a reprodução do cartão do Discord. São
  as cores do Discord, não do Palco; não use fora da prévia.

### Named Rules
**The One Light Rule.** Uma luz por página, sempre sobre o palco, sempre de cima. Painéis comuns não
recebem luz nem degradê no fundo.

**The Red Pedal Rule.** O vermelho (#E0141C) é o pedal e o amplificador. Erro usa Brasa; ação usa o
degradê âmbar → laranja.

**The Lit Means Live Rule.** O degradê âmbar → laranja marca o que está aceso agora (ligado, hoje,
progresso, ação principal). Se não está ao vivo nem é a ação principal, é cinza.

## Typography

**Display Font:** Archivo, fonte variável com eixos [peso, largura], em `assets/fonts/Archivo.ttf`
(com Segoe UI se não carregar)
**Body Font:** Segoe UI Variable Text no Windows 11 (eixos [peso, tamanho óptico]); Segoe UI comum no
Windows 10 (`segoeui`, `seguisb` a partir de 600, `segoeuib` a partir de 700)

**Character:** A Archivo larga e pesada dá voz de cartaz de show aos nomes e números; a Segoe UI deixa o
resto com cara de programa do Windows, legível e calmo.

### Hierarchy
- **Display XL** (Archivo 800, largura 125, 46 px, linha 0,98, cor glow): o nome do preset no palco do
  Painel e a versão na página de Atualização. Quebra equilibrada em até duas linhas (`balanced`).
- **Display LG** (Archivo 800, largura 125, 38 px): o palco sem Guitar Rig aberto e o título da
  primeira abertura.
- **Headline** (Archivo 800, largura 125, 30 px, cor text): título das páginas Estatísticas e Ajustes.
- **Stat** (Archivo 800, largura 118, 34 px) e **Stat SM** (24 px, cor glow): minutos de hoje na meta;
  números ao lado do gráfico, com os tempos em horas e minutos ("7 h 34 min", "87 h 46 min").
- **Title** (Archivo 700, largura 112, 15 px, linha 1,2): título de cada painel ("Meta de hoje",
  "Conexões", "Prática").
- **Body Lead** (14 px, linha 1,5, text-lead): o parágrafo sob o título do palco.
- **Body** (13,5 px, linha 1,3): valores de campos e linhas de conexão. **Label** (13,5 px, 600): nome
  de cada opção dos Ajustes.
- **Body SM** (13 px, linha 1,4 a 1,45, muted): dicas, notas e explicações.
- **Button** (13 px, 600) e **Button Primary** (13,5 px, 700, on-accent).
- **Caption** (12 a 12,5 px) e **Micro** (10,5 a 11,5 px, faint ou icon-off): eixos do gráfico,
  contadores, rótulos do trilho. Nada abaixo de 10,5 px.

### Named Rules
**The Integer Pixel Rule.** O tamanho da fonte é arredondado para um inteiro depois de multiplicado pela
escala (`font()`): em tamanho pequeno o hinting arredonda cada letra, e um tamanho quebrado só muda as
quebras de linha. Atenção: o Python arredonda o ,5 para o par, então em 100 % 10,5 vira 10, 12,5 vira
12 e 13,5 vira 14. Confira a quebra em 1×, 1,25×, 1,5× e 2×.

**The Two Voices Rule.** Archivo só em títulos e números grandes; nenhum texto corrido, botão ou rótulo
em Archivo. Sem caixa-alta, sem espaçamento entre letras, sem rótulo pequeno acima do título.

## Layout

Janela de 960 × 640 px lógicos (mínimo 860 × 560); a primeira abertura tem área interna de 720 × 568,
sem trilho. O trilho tem 78 px, com o ícone do pedal (34 px) no topo, uma entrada por página (64 px de
largura, ícone de 20 px sobre rótulo, 6 px entre elas) e a versão nova presa embaixo.

As páginas têm margem de 24 px dos lados, 20 px em cima e 20 a 24 px embaixo, e 14 px entre blocos. O
palco tem 28 px de respiro interno; os painéis, 21 px dos lados e 19 px em cima, com o título seguido
de 30 px até o conteúdo. Linhas de opção são separadas por uma linha panel-line, não por caixas.

Os Ajustes têm um painel fixo de 320 px à direita (a prévia do perfil, 276 px de largura). O Painel
divide o palco entre o nome (esquerda) e o cartão de 290 px (direita), e embaixo dois painéis de mesma
largura. Controles têm 34 px de altura; o botão principal, 38. A página rola com a roda (60 px por
passo) e mostra uma barra de rolagem de 4 px só quando não cabe.

Toda medida é lógica: desenhe com o `Painter`, nunca em pixels de tela.

Os exemplos têm 960 px, mas a pessoa pode alargar a janela: o que tem tamanho fixo deixa um vazio.
Painéis, campos e barras crescem com a largura. O calendário mantém o quadradinho perto de 13 px e
mostra mais semanas (16 no mínimo) até encostar na borda (`calendar_grid`). Nas listas de presets e
amplificadores, o nome fica com a coluna do exemplo (200 px, ou o que um nome comprido precisar) e a
barra fica com o resto.

## Elevation & Depth

A profundidade vem de camadas de tom (bg → rail → stage → panel → field → selected), não de sombra. Os
painéis são planos com contorno de 1 px um tom acima. A luz é uma elipse radial (`radial_light`) presa
ao palco, com centro acima da borda superior: âmbar a ~0,30–0,36 de opacidade passando a laranja a
~0,12–0,15 e sumindo em ~72 %. Com o Guitar Rig fechado, a luz do Painel vira um cinza-azulado a 0,12.

### Shadow Vocabulary
- **Cartão flutuante** (preto a 75 %, deslocamento 22, desfoque 44, recuo −14): só o cartão do Discord,
  que é a única peça "de fora" sobre o palco.
- **Brilho da conquista** (laranja a 80 %, deslocamento 10, desfoque 22, recuo −10): só a conquista
  ganha, que acende.
- **Botão do deslizante** (preto a 50 %, deslocamento 1, desfoque 4): o círculo branco do deslizante.

### Named Rules
**The Flat Panel Rule.** Painel não tem sombra. Sombra só onde algo flutua (o cartão do Discord) ou
acende (a conquista ganha).

## Shapes

Cantos sempre arredondados e suavizados (desenho 4× maior e reduzido). Quanto maior a peça, maior o
raio: palco 18, painel 16, conquista 15, item do trilho 12, botão principal 11, campos e botões 10,
cartão do Discord e segmentos 8, item da lista de opções 6. Pílulas e chaves são cápsulas inteiras;
trilhos de progresso usam metade da altura. Barras do gráfico só têm canto em cima
(`top_rounded_bar`). A linha da meta passa na frente das barras: tracejado âmbar de 1,5 px (5 ligado,
4 desligado), com um contorno na cor do palco só onde cruza uma barra, para não sumir na barra de
hoje. O espaço vazio do cartão é um contorno tracejado (6 ligado, 4 desligado) de raio 8.

## Components

### Buttons
- **Shape:** cantos de 10 (secundário, 34 de altura) e 11 (principal, 38 de altura).
- **Primary:** degradê horizontal âmbar → laranja, texto on-accent em 13,5/700. Um por tela (Atualizar
  agora; o botão final da primeira abertura).
- **Secondary:** btn com contorno btn-line, texto 13/600, 14 px de respiro. O botão do palco (Pausar)
  usa a mesma forma num tom um pouco mais escuro (btn-stage) e pode ter ícone de 13 px e a seta da lista.
- **Hover / Focus:** não há hover desenhado nos botões da página; o cursor vira mão. O foco do teclado é
  o contorno âmbar (ver Navegação).
- **Disabled:** o degradê do principal é apagado a 45 % sobre o fundo (`update_page.py`).

### Chips
- **Pílulas da cadeia:** cápsula de fundo branco a 6 % com contorno a 9 %, texto 12,5/500; 6 px entre
  elas, quebram em linhas. O amplificador é a única pílula vermelha, com texto branco 12,5/600.
- **Segmentado:** fundo field com contorno panel-line (raio 11); o segmento escolhido é selected com
  texto text, os outros muted, 12,5/600.

### Cards / Containers
- **Palco:** stage, raio 18, luz radial, 28 de respiro. Um por página, no topo.
- **Painel:** panel, raio 16, contorno panel-line, título Title. Sem sombra.
- **Conquista:** quadrado de 52 com raio 15; ganha = degradê âmbar → laranja com ícone escuro e brilho;
  não ganha = tom escuro com ícone dim e trilho de progresso de 4 px.
- **Prévia do Discord:** reproduz o cartão real nas cores do Discord (card, raio 8, imagem de 64 com o
  amplificador desenhado, quatro linhas, botões de 30 px). Montada pelas mesmas funções que mandam a
  atividade. Embaixo, tracinhos de 16 × 4 indicam o cartão do rodízio (âmbar o atual).

### Inputs / Fields
- **Style:** field, contorno field-line, raio 10, 34 de altura, texto Body com 12 px de respiro. O texto
  digitável é um `tk.Entry` posto por cima do desenho; o texto de exemplo fica em faint.
- **Focus:** contorno âmbar e um halo focus-ring de 3 px (raio 13) em volta.
- **Error:** contorno laranja no campo e a mensagem em Brasa logo abaixo, dizendo o que fazer.
- **Escolha:** igual ao campo, com a seta `down` de 14 px; abre uma lista de opções (field, raio 10,
  itens de 32 px, item com o mouse em selected, o atual com um `check` âmbar).
- **Chave:** 38 × 22; ligada = degradê âmbar → laranja com círculo branco à direita; desligada =
  switch-off com círculo cinza-claro à esquerda.
- **Deslizante:** trilho de 6 px em track, preenchido no degradê, círculo branco de 16 com sombra; as
  setas do teclado mexem nele.

### Navigation
- **Trilho:** ícone de traço de 20 px sobre rótulo 10,5/600. Página atual: fundo rail-on, ícone âmbar,
  rótulo text. Mouse por cima: fundo field. Fora: icon-off. A versão nova fica embaixo, em âmbar, com
  um ponto laranja.
- **Teclado:** Tab e Shift+Tab percorrem trilho, página (de cima para baixo) e painel da direita; Enter
  ou espaço acionam; setas mexem no deslizante; na lista de opções, setas escolhem, Enter confirma, Esc
  fecha. O controle com foco ganha um contorno âmbar de 2 px (no mínimo 2 px de tela), 3 px para fora,
  com os cantos do controle + 3. Clicar com o mouse apaga o contorno.

### Ícones
Traço só, caixa de 24 × 24, traço de 1,8 (2,2 a 2,6 nos ícones pequenos de controle), pontas redondas,
definidos como caminhos no `ICONS` do `ui_kit.py`. Cor única por ícone. Emoji colorido só aparece
dentro do texto do cartão do Discord, porque é o que o Discord mostra.

### Movimento
Quase nenhum. Cada mudança redesenha a imagem e troca de uma vez (pedidos seguidos se juntam em um
desenho). O Painel se redesenha a cada 1 s para contar o tempo do cartão e o "troca em"; as outras
páginas, a cada 10 s; minimizada, nada é desenhado. Não há transição, fade nem animação.

## Do's and Don'ts

### Do:
- **Do** pegar cor, estilo de texto e peça do `gr7_presence/ui_kit.py`; cor nova entra lá, com nome.
- **Do** começar uma tela nova com um palco (stage, raio 18, `radial_light`) e pôr o resto em painéis
  (panel, raio 16, título Title), com 24 px de margem e 14 px entre blocos.
- **Do** desenhar em px lógicos pelo `Painter` e conferir em 1×, 1,25×, 1,5× e 2×, e em janelas de
  860, 960, 1120 e 1920 px de largura.
- **Do** dar a todo controle clicável uma `Region` com o `radius` do desenho, para o Tab chegar nele e o
  contorno âmbar acompanhar o canto.
- **Do** escrever o erro em Brasa, em palavras simples, dizendo o que fazer.
- **Do** manter texto em faint ou mais claro (4,5:1 no mínimo); dim só para ícone e ponto.
- **Do** mostrar a tela nova ao dono do projeto (exemplo ou captura) antes de virar código.

### Don't:
- **Don't** usar o vermelho #E0141C fora do amplificador e do pedal.
- **Don't** pôr luz ou degradê em mais de um palco por página, nem em painel comum.
- **Don't** usar Archivo em texto corrido, botão ou rótulo; nem caixa-alta ou rótulo pequeno acima de
  título.
- **Don't** fazer uma fileira de painéis iguais do mesmo peso como primeira vista.
- **Don't** usar arte, logo ou marca da Native Instruments; o ícone é o pedal de `tools/icone_pedal.py`.
- **Don't** usar as cores do cartão do Discord (card, card-muted, card-button) fora da prévia.
- **Don't** desenhar com tamanho fixo em pixels de tela nem criar animação.
