# Arquitetura

Como as peças do GR7 Presence conversam. As regras e as armadilhas estão no [`AGENTS.md`](../AGENTS.md);
o porquê de cada escolha, em [`decisoes.md`](decisoes.md).

## Visão geral

```mermaid
flowchart LR
    GR7["Guitar Rig 7<br/>(programa ou VST3)"]
    subgraph Programa["GR7 Presence (pythonw, sem console)"]
        DET[detector]
        APP["app<br/>loop de 5 s"]
        TLE[gr7_state<br/>LastEditBuffer.tle]
        LIVE[live<br/>captura + OCR]
        LIB[preset_library<br/>presets .ngrr]
        PRES[presence<br/>cartões]
        IPC[discord_ipc]
        ST[stats]
        UPD[updates]
        TRAY[tray<br/>bandeja]
    end
    DISCORD[Discord desktop]
    GH[GitHub Releases]

    GR7 -- processo --> DET --> APP
    GR7 -- arquivo ao fechar --> TLE --> APP
    GR7 -- janela --> LIVE --> APP
    LIB --> APP
    APP --> PRES --> IPC -- pipe local --> DISCORD
    APP --> ST
    APP --> UPD -- 1x por dia --> GH
    APP -- status, versão nova --> TRAY
```

## O passo do loop

A cada 5 segundos, o `app.tick()`:

1. Recarrega o `config.json` se ele mudou, e dispara a consulta de versão nova se já passou um dia
   (em outra thread, para não segurar o loop).
2. Pergunta ao `detector` se o Guitar Rig está aberto: como programa (`Guitar Rig 7.exe`) ou como VST3
   carregado numa DAW conhecida. Mudou o processo? Fecha a sessão de estatísticas e abre outra.
3. Descobre o estado atual (`_current_state`):
   - o `LastEditBuffer.tle`, que vale para a abertura (o Guitar Rig reabre como fechou);
   - a captura da janela lida pelo OCR, que dá o nome do preset na tela e se o rack está vazio;
   - o nome lido é casado com a biblioteca de presets, e o `.ngrr` encontrado dá o amp, a cadeia e as
     tags;
   - os arquivos de áudio abertos pelo processo dão a faixa do Tape Deck.
4. Soma o tempo nas estatísticas (`dados\stats.json`, salvo a cada minuto e no fim da sessão).
5. Monta os cartões (`presence.build_cards`) e envia o da vez ao Discord. Os cartões se revezam a
   cada `rotate_seconds`. Quando o preset muda, o primeiro cartão vai na hora.

## Threads

| Thread | O que roda | Por quê |
|---|---|---|
| Principal | `tkinter` oculto, janela principal | O tkinter exige a thread principal |
| pystray | Ícone e menu da bandeja (`run_detached`) | Tem o próprio laço de mensagens do Windows |
| `presence` | O loop do `app` | Captura, OCR e Discord não podem travar a interface |
| `updates` | Uma consulta ao GitHub, e termina | Rede lenta não pode atrasar o loop |
| `download` | Baixa e confere o zip depois do "Atualizar agora" | A janela continua respondendo durante o download |

## Atualização com um clique

1. A página Atualização da janela principal mostra as notas da release. Ela abre pelo item da versão
   nova, no pé da barra lateral, ou pelo menu da bandeja. Em "Atualizar agora", a thread `download`
   baixa o anexo `GR7-Presence.zip` (só de uma release deste repositório) e confere o sha256 informado
   pela API.
2. `updates.start_updater` copia o `tools/atualizar.py` da versão instalada para a pasta temporária e o
   inicia, separado, com o PID do programa. O programa fecha como no "Sair" (salva as estatísticas e limpa
   o Discord).
3. O atualizador espera o PID sumir, confere o zip, guarda os arquivos que vai trocar em
   `dados\atualizacao\anterior`, extrai por cima e roda `tools\instalar.ps1 -Atualizacao`, que instala as
   dependências, gera o ícone e abre o programa.
4. Falhou qualquer passo: devolve os arquivos guardados, apaga os que a versão nova criou e reabre a
   versão anterior. O resultado vai para `dados\atualizacao.json`, e a bandeja avisa na próxima abertura.

As threads conversam pela fila do `TrayUI`, lida com `root.after` a cada 250 ms. Nenhuma outra
thread mexe em widget do tkinter.

## A janela principal

Uma janela só (`main_window.py`), com uma barra lateral e uma página para cada assunto. Por enquanto
existem as páginas Painel, Estatísticas e Ajustes. Cada página tem
`render(largura, escala, t)` e devolve uma imagem do Pillow com as áreas clicáveis. O Tkinter só mostra
essa imagem num `Canvas`, rola com a roda do mouse, repassa os cliques e redesenha a cada 10 segundos.

```mermaid
flowchart LR
    ST[stats<br/>números] --> PAGE[stats_page<br/>desenha a página]
    KIT[ui_kit<br/>cores, fontes, peças] --> PAGE
    PAGE -- imagem + áreas clicáveis --> WIN[main_window<br/>Canvas, rolagem, cliques]
    TRAY[tray] -- abre --> WIN
```

As medidas são as dos exemplos aprovados, em pixels lógicos. O `Painter` multiplica pela escala de DPI
do Windows, e por isso o desenho fica nítido em qualquer escala.

O que não dá para desenhar fica com o Tkinter: os campos de texto são `tk.Entry` postos por cima do
desenho do campo (a página devolve onde ficam), a lista de opções é uma janelinha sem borda, e o
controle deslizante usa o arrastar do mouse. A página de Ajustes tem ainda um painel fixo à direita (a
prévia), que não rola junto com o formulário.

As opções mudadas na janela são gravadas com `Config.update`, que faz o loop recarregar o arquivo na
volta seguinte (idioma, detecção de DAWs, reenvio do cartão), sem reiniciar.

O Painel só lê o que o loop guardou na última volta, sem perguntar nada ao Guitar Rig nem ao Discord:
`app.last_state` (preset, alvo, faixas, estado do rack), `app.showing` (a atividade que está no perfil,
a posição no rodízio e quando foi enviada), `app.screen` (lendo, minimizada ou sem OCR) e
`app.discord_connected`. Ele se redesenha a cada segundo, para o tempo do cartão andar.

## Arquivos de dados

Tudo em `dados\`, dentro da pasta do programa (ver a decisão D3):

| Arquivo | Conteúdo |
|---|---|
| `config.json` | Opções (README › Configuração); recarregado ao salvar |
| `stats.json` | Sessões de prática; um arquivo ilegível é guardado como `stats.corrompido-<horário>.json` |
| `live_state.json` | Último preset lido na tela, para sobreviver a um reinício com o Guitar Rig minimizado |
| `gr7_presence.log` | Log rotativo (512 KB, 3 arquivos) |
| `atualizacao.log` | Passo a passo de cada atualização, com a saída do instalador |
| `atualizacao.json` | Resultado da última atualização; a bandeja avisa e apaga |
| `atualizacao\anterior\` | Os arquivos trocados na última atualização, para o caminho de volta |
| `palavras-privadas.txt` | Só para quem publica versões: a lista que o `empacotar.py` procura |

## Formatos do Guitar Rig

- **`LastEditBuffer.tle`** (`%LOCALAPPDATA%\Native Instruments\Guitar Rig 7`): blocos
  `atad <versão> <tipo invertido> bilz <tamanho comprimido> <tamanho original> <zlib>`, com três XMLs:
  `<soundinfo>` (nome, autor, tags), `<gr-instrument-chunk>` (o rack) e `<user_state>` (caminho do
  último preset).
- **`.ngrr`** (presets de fábrica em `Common Files\Native Instruments\Guitar Rig 7\Rack Presets` e do
  usuário em `Documentos\Native Instruments\User Content\Guitar Rig 7\Rack Presets`): árvore binária de
  blocos `hsin`/`DSIN` com os mesmos XMLs sem compressão. O programa só precisa dos XMLs.

`tests/sinteticos.py` gera os dois formatos com dados inventados, e é a melhor referência executável.

## Distribuição

```mermaid
flowchart LR
    PR[Pull Request] -- CI: testes + dados pessoais --> MAIN[main]
    MAIN -- tag vX.Y.Z --> REL[workflow Release]
    REL -- testes, notas, empacotar --> ZIP[GR7-Presence.zip na release]
    ZIP -- aviso na bandeja em até 1 dia --> USO[quem usa: Atualizar agora]
```

O zip leva só arquivos versionados, sem os testes e sem as ferramentas de publicação. O instalador
gera o ícone a partir do Guitar Rig da própria máquina.
