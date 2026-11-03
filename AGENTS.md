# AGENTS.md: contexto do projeto para pessoas e assistentes de IA

> **Leia este arquivo inteiro antes de mudar qualquer coisa.**
>
> O GR7 Presence é mantido com a ajuda de assistentes de IA, sessão após sessão. Nenhum assistente
> lembra da sessão anterior: o que não está escrito aqui (ou em `docs/`) vai ser reinventado, quase
> sempre de um jeito diferente. Vale para Claude Code, Copilot, Cursor, Codex ou qualquer outro. Se
> você é uma pessoa, as regras são as mesmas.

## 1. O que é o projeto

Um programa de bandeja para Windows que mostra no perfil do Discord o que a pessoa está tocando no
**Guitar Rig 7** (Native Instruments): o preset, o amplificador, a cadeia de efeitos, a faixa do Tape
Deck, o tempo de uso e estatísticas de prática. Quem usa não é programador: baixa um zip da página de
releases, roda o `instalar.bat` e espera que funcione sem mexer em nada.

O difícil não é o Discord, é **descobrir o estado do Guitar Rig de fora dele**. O Guitar Rig não tem
API: o `LastEditBuffer.tle` só é gravado quando ele fecha, e a interface (Qt/QML) não expõe o nome do
preset para acessibilidade. Por isso o preset ao vivo vem de uma captura da janela lida pelo OCR do
Windows, conferida contra a biblioteca de presets (`docs/arquitetura.md`, `docs/decisoes.md`).

O repositório é **público** e as releases são a forma de distribuir: cada versão gera um zip pela CI,
e o programa avisa quem usa quando sai uma nova.

## 2. Regras inegociáveis

1. **Nada pessoal nem de terceiros no repositório.** Arquivos do Guitar Rig de alguém (`.tle`,
   `.ngrr`), presets e arte da Native Instruments (o logo sai do `.exe` na instalação), caminhos como
   `C:\Users\<nome>`, contas de Discord, e-mails, nomes de faixas que alguém tocou. Testes usam
   `tests/sinteticos.py`. **Por quê:** o histórico público não se apaga de verdade, e o logo é marca
   registrada. A CI confere com `tools/empacotar.py --verificar` (a lista de palavras privadas fica no
   secret `GR7_PALAVRAS_PRIVADAS`, nunca no código).
2. **Commits e PRs só no nome do dono do repositório.** Sem `Co-Authored-By` de assistente de IA, sem
   "Generated with", sem menção à ferramenta no título ou na descrição. Commits com o e-mail
   `noreply` do GitHub, nunca o e-mail pessoal.
3. **Toda mudança entra por Pull Request com a CI verde.** A `main` é protegida e é dela que sai a
   release. Mesmo sozinho: o PR guarda o motivo e roda os testes no Windows.
4. **Mudou algo que quem usa percebe? O `CHANGELOG.md` muda no mesmo PR**, na seção *Não lançado*. É
   esse texto que vira a nota da release que as pessoas leem antes de atualizar.
5. **O loop nunca cai.** Arquivo corrompido, Discord fechado, Guitar Rig minimizado, sem internet: o
   programa registra no log e segue. Quem usa não vê terminal; um erro não tratado é um programa que
   "parou de funcionar" sem explicação.
6. **Os dados de quem usa ficam em `dados\`, dentro da pasta do programa, nunca em `%APPDATA%`.** Ver
   a armadilha do MSIX na seção 7. A atualização (extrair o zip por cima) não pode tocar nessa pasta.
7. **Respeite os limites do Discord** que o `presence.py` impõe: troca de cartão a cada 15 s ou mais,
   textos de 2 a 128 caracteres (contados em UTF-16), rótulo de botão até 32. Passar disso faz o
   Discord descartar a atividade em silêncio.
8. **Dependência nova só com motivo, licença permissiva e wheel para Windows.** O instalador roda na
   máquina de quem não tem compilador; um pacote que precisa compilar quebra a instalação.
9. **Compatível com Python 3.10 a 3.13**, que é o que o instalador aceita. A CI testa os extremos.

## 3. Arquitetura

```
detector ──► app (loop de 5 s) ──► presence (cartões) ──► discord_ipc ──► Discord
               │
               ├── gr7_state      LastEditBuffer.tle e presets .ngrr
               ├── live           captura da janela + OCR do Windows → nome do preset na tela
               ├── preset_library nome lido → arquivo .ngrr → amp, cadeia, tags
               ├── stats          tempo de prática em dados\stats.json
               └── updates        releases do GitHub, uma vez por dia
tray (thread principal, tkinter + pystray) ◄── status e aviso de versão nova
```

| Módulo | Responsabilidade | O que não faz |
|---|---|---|
| `__main__.py` | Linha de comando, log, instância única, liga o loop à bandeja | Regra de apresentação |
| `app.py` | O loop: decide o estado atual e quando atualizar o Discord | Ler arquivo do Guitar Rig diretamente |
| `detector.py` | Acha o Guitar Rig aberto (programa ou VST3 numa DAW) | Saber qual preset está carregado |
| `gr7_state.py` | Lê `.tle` e `.ngrr` e devolve um `PresetInfo` | Acessar a janela, falar com o Discord |
| `live.py` | Captura a janela, OCR, rack vazio, faixas do Tape Deck | Decidir o que mostrar |
| `preset_library.py` | Índice dos presets de fábrica e do usuário, casamento de nomes do OCR | OCR |
| `presence.py` | Monta os cartões e o payload, com os limites do Discord | Rede, estado |
| `discord_ipc.py` | Pipe local do Discord (handshake, `SET_ACTIVITY`) | Montar texto |
| `assets.py` | Plano B quando o Discord não reconhece as imagens | — |
| `stats.py` / `stats_window.py` | Sessões de prática e a janela de estatísticas | — |
| `tray.py` | Ícone, menu, notificações | Lógica de presença |
| `updates.py` | Consulta a última release, baixa o zip conferindo o sha256, entrega ao atualizador | Trocar arquivos ou atualizar sem a pessoa confirmar |
| `update_window.py` | A janela "Atualizar o GR7 Presence" (notas e botão) | Baixar ou instalar |
| `tools/atualizar.py` | Roda depois que o programa fecha: troca os arquivos, roda o instalador, volta se falhar | Importar o programa ou qualquer pacote fora da biblioteca padrão |
| `config.py` / `migrate.py` | `dados\config.json` com recarga ao vivo; migração de versões antigas | — |
| `tools/` | Instalador, empacotador, notas da release, ícones | Rodar junto com o programa |

Stack: Python puro com `psutil`, `pystray`, `Pillow` e, opcional, os pacotes `winrt` do OCR. Não troque
nem acrescente peças por conta própria: "o assistente sugeriu" não é justificativa. Abra uma issue.

## 4. Como rodar e testar

```bash
.venv\Scripts\python -m unittest discover -s tests -t .   # testes (os de instalação real pulam sem o Guitar Rig)
.venv\Scripts\python -m gr7_presence --console --debug    # sem bandeja, log no terminal
.venv\Scripts\python -m gr7_presence --preview            # cartões que iriam para o Discord
.venv\Scripts\python tools\inspect_gr7.py                 # o que está sendo lido do Guitar Rig agora
.venv\Scripts\python tools\empacotar.py --verificar       # a mesma conferência de dados pessoais da CI
```

Teste que passa não basta quando a mudança é visível: confira no Discord ou na bandeja, e diga no PR
o que foi visto e o que não deu para ver.

## 5. Convenções

| O quê | Idioma e forma | Exemplo |
|---|---|---|
| Nomes no código | Inglês, `snake_case` | `rack_is_empty`, `PresetLibrary` |
| Comentários, docstrings, log, docs | Português, explicando o **porquê** | `# minimizada não renderiza` |
| Textos da interface | Pelas chaves do `i18n.py`, em pt e en | `t("menu_update", version=...)` |
| Commits | `tipo: efeito`, em português | `fix: preset com nome cortado aparece completo` |
| Ramos | `tipo/descricao-curta` | `feat/aviso-de-versao` |

Tipos de commit: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`. O corpo explica o porquê.
`Closes #N` no PR fecha a issue (a palavra-chave precisa ser em inglês).

Lançar uma versão: `docs/lancar-versao.md`. Nunca crie a tag à mão sem seguir o roteiro.

## 6. Trabalhando com o assistente

- Mudanças cirúrgicas; nada de "melhorar de passagem" arquivos fora do escopo. O que estiver errado
  fora do escopo vira issue.
- Teste junto com a mudança. "Faça os testes passarem" não é pedido válido: corrija o defeito.
- Antes de afirmar como o Guitar Rig se comporta, meça (capture, leia o arquivo, rode o
  `inspect_gr7.py`). Várias suposições razoáveis deste projeto estavam erradas (seção 7).
- Leia o diff inteiro antes do commit: quem assina é o dono do repositório.

## 7. Armadilhas conhecidas

**"Abri pelo Menu Iniciar e não aparece nada no Discord", mas pelo terminal funciona.** Programas
abertos de dentro de um app empacotado (MSIX, como o app desktop do Claude ou o Python da Microsoft
Store) têm o `%APPDATA%` redirecionado para `%LOCALAPPDATA%\Packages\<app>\LocalCache\Roaming`. O
programa aberto pelo assistente e o aberto pela pessoa liam configurações diferentes. Por isso os
dados ficam em `dados\` e o instalador recusa o Python da Store (`\WindowsApps\`). Para testar como a
pessoa vê: `Start-Process explorer.exe -ArgumentList '"<atalho .lnk>"'`.

**O preset não muda no perfil.** O `LastEditBuffer.tle` só é gravado quando o Guitar Rig fecha; o
estado ao vivo vem do OCR. Com a janela minimizada o `PrintWindow` não desenha nada e fica o último
preset lido (guardado em `dados\live_state.json` para sobreviver a um reinício).

**"IVP Bass" lido como "Bass".** Nomes curtos somem no OCR em tamanho real: a captura é ampliada 2×
(`OCR_SCALE`). Trocas típicas do OCR (`l`→`I`, `rn`→`m`, espaço sumido) são tratadas no
`skeleton()` do `preset_library.py`.

**Nome longo aparece como "ABCD - Post Punk Lead 6 (R...".** O Guitar Rig corta o nome na tela; o
casamento por prefixo recusa empate entre vários presets em vez de chutar.

**"Clear Rack" mantém o nome do preset no topo.** Por isso o `rack_is_empty` olha a área do rack, e o
estado "Timbre próprio" vale até outro preset ser carregado.

**"Split", "Split B", "Split Mix", "CrossOver…" não são efeitos.** São os marcadores dos caminhos
paralelos no XML do rack; ficam em `_CHAIN_IGNORE`.

**A atualização não pode rodar com o programa aberto.** No Windows, um `.pyd` carregado fica preso:
com o GR7 Presence aberto, o `pip` não consegue trocar os do `psutil` e do `Pillow`. Por isso o
`tools/atualizar.py` espera o processo fechar e só importa a biblioteca padrão: ele mesmo roda com o
Python do `.venv` enquanto o `pip` atualiza esse ambiente.

**Ícone pequeno em branco no Discord.** O Discord guarda em cache a lista de imagens do app; se a
chave não é reconhecida, o `assets.py` passa a mandar o link do CDN. O ícone ao lado do nome só
atualiza com Ctrl+R no Discord.

**Ler o pipe do Discord numa thread trava a escrita.** O pipe é síncrono no Windows e serializa as
operações: o `discord_ipc.py` consulta com `PeekNamedPipe` em vez de deixar uma leitura pendurada.

**`Start-Process -Wait` não volta.** Ele espera também os filhos (o `pythonw` da bandeja). Não use para
abrir o programa em script.

**Teste que depende da data de modificação falha só às vezes.** A biblioteca de presets percebe preset
novo pela data da pasta, e o `PresetReader` pela data do arquivo. Numa máquina rápida, como a da CI,
duas gravações seguidas caem no mesmo instante e a data não muda: o teste passou quatro vezes e falhou
na release 1.0.0. Nos testes, avance a data com `os.utime` em vez de contar com o relógio.

**`.ps1` sem BOM estraga os acentos.** O PowerShell 5.1 lê UTF-8 sem BOM como ANSI. O `.editorconfig`
fixa `utf-8-bom` para `.ps1`.

## 8. Onde encontrar o resto

| Preciso de… | Está em |
|---|---|
| Como as peças conversam, threads, arquivos de dados | `docs/arquitetura.md` |
| Por que foi feito assim (OCR, IPC próprio, `dados\`, sem auto-update…) | `docs/decisoes.md` |
| Publicar uma versão | `docs/lancar-versao.md` |
| Refazer o app no Discord Developer Portal | `docs/app-do-discord.md` |
| Montar o ambiente, abrir PR | `CONTRIBUTING.md` |

> **Este arquivo é vivo.** Convenção nova ou armadilha nova entra aqui no mesmo Pull Request que a
> introduz. Se o código diverge deste documento, um dos dois está errado: descubra qual antes de seguir.
