# GR7 Presence 🎸

[![Versão](https://img.shields.io/github/v/release/PedroMiranda243/gr7-presence?label=vers%C3%A3o)](https://github.com/PedroMiranda243/gr7-presence/releases/latest)
[![CI](https://github.com/PedroMiranda243/gr7-presence/actions/workflows/ci.yml/badge.svg)](https://github.com/PedroMiranda243/gr7-presence/actions/workflows/ci.yml)
[![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)](LICENSE)

Mostra no seu perfil do Discord que você está tocando no **Guitar Rig 7**, com o ícone oficial, o tempo de uso e detalhes do seu timbre, que se revezam a cada 20 segundos:

| Cartão | Linha 1 | Linha 2 | Ícone pequeno (passe o mouse) |
|---|---|---|---|
| Rig | 🎸 Auto Rhythm | 🔊 Plex · AutoFilter → Stomp Compressor → Tube Compressor +3 | 🟧 amp: rack completo |
| Estilo | 🎸 Auto Rhythm | 🕺 Funk & Soul · Crunch · Wah-Wah · Distorted | 🟪 pedal: "Preset de fábrica por NI Design Collective" |
| Backing track | 🎶 Backing track | Artista - Nome da Música | 🟩 fita: "Faixa carregada no Tape Deck" |
| Prática | 🎸 Auto Rhythm | ⏱ Hoje 1h12 · 🔥 5 dias seguidos | 🔥 total de horas e sessões |

O cartão de backing track só aparece quando há uma faixa aberta no Tape Deck. O cronômetro ("há 01:23:45") conta desde a hora em que o Guitar Rig foi aberto.

## ⬇️ Baixar

**[Baixar a versão mais recente (GR7-Presence.zip)](https://github.com/PedroMiranda243/gr7-presence/releases/latest/download/GR7-Presence.zip)**

Precisa de Windows 10 ou 11, do Guitar Rig 7 e do Discord desktop (o Discord no navegador não mostra Rich Presence).

1. Clique com o botão direito no zip e escolha **Extrair tudo...**. Use uma pasta fixa, como Documentos: o programa roda de lá.
2. Na pasta extraída, dê dois cliques em **`instalar.bat`**. Se o Windows mostrar "O Windows protegeu o computador", clique em **Mais informações › Executar assim mesmo**.
   - Sem Python no PC, o instalador oferece instalar o 3.11 sozinho (é só responder S).
   - No fim, ele pergunta se deve abrir junto com o Windows e já abre o programa na bandeja, perto do relógio.
3. Abra o Guitar Rig 7 e veja seu perfil.

> No Discord, **Configurações › Privacidade de atividade › "Compartilhar sua atividade detectada com outras pessoas"** precisa estar ligada.

## 🔔 Atualizações

- **O programa avisa sozinho.** Uma vez por dia ele confere se saiu versão nova. Quando sai, aparece uma notificação e o item **⬆️ Atualizar para a versão X** no menu do ícone da bandeja.
- **Para atualizar, um clique:** o item abre uma janela com o que muda. Em **Atualizar agora**, o programa baixa a versão nova, confere se o arquivo é o mesmo publicado aqui, fecha, instala e abre de novo sozinho, em 1 ou 2 minutos. Se algo der errado, a versão que você tinha volta, e o motivo fica em `dados\atualizacao.log`.
- **Suas estatísticas e configurações ficam guardadas.** A pasta `dados` não é tocada.
- **Atualizar à mão também funciona** (e é o caminho para quem está na 1.0.0, que ainda não tem o botão): botão direito na bandeja › **Sair**, extraia o zip novo **na mesma pasta**, substituindo os arquivos, e rode o `instalar.bat` de novo.
- **Quer um e-mail a cada versão?** Com uma conta no GitHub, clique em **Watch › Custom › Releases** no topo desta página.
- **O que mudou em cada versão:** [página de releases](https://github.com/PedroMiranda243/gr7-presence/releases) ou o [`CHANGELOG.md`](CHANGELOG.md).

## Recursos

- **Detecção automática.** Aparece no Discord quando o Guitar Rig 7 abre e some quando ele fecha.
- **Preset ao vivo.** A cada 5 segundos, o programa captura a janela do Guitar Rig (funciona mesmo atrás de outras janelas) e lê o nome do preset com o OCR do Windows. O nome é conferido com a biblioteca de presets (os de fábrica e os seus, em Documentos), e de lá vêm o amplificador, a cadeia de efeitos, as tags e o autor. Com o Guitar Rig minimizado, fica o último preset lido.
- **Rack vazio e timbre montado do zero.** Depois de um "Clear Rack", o perfil mostra "🎛️ Rack vazio" e, quando você acrescenta componentes, "🎛️ Timbre próprio", até carregar outro preset.
- **Backing track.** Mostra a faixa aberta no Tape Deck, com o nome limpo: sem "backing track", "w/ vocals" e afins. As gravações temporárias do próprio Tape Deck são ignoradas.
- **Modo plugin.** Com o Guitar Rig 7 aberto como VST3 numa DAW (REAPER, FL Studio, Ableton, Studio One, Cubase, Bitwig, Cakewalk…), mostra "🎛️ Guitar Rig 7 no REAPER".
- **Estatísticas de prática.** Gráfico dos últimos 14 dias (ou por semana, ou por mês) com a meta do dia, sequência de dias seguidos 🔥 (vale a partir de 5 min por dia), recorde, conquistas, calendário dos dias tocados, presets e amps mais usados e as sessões recentes. Tudo fica no seu PC.
- **Janela do programa.** Painel com o que está no seu perfil agora, Estatísticas e Ajustes, no visual escuro do programa.
- **Bandeja do sistema.** Ponto verde quando está no Discord, cinza quando está esperando. Menu com pausar, estatísticas, configurações, iniciar com o Windows e a versão instalada.
- **Ícone próprio.** Um pedal vermelho na bandeja, na barra de tarefas e nos atalhos, diferente do ícone do Guitar Rig 7 para não confundir os dois abertos ao mesmo tempo.
- **Robusto.** Se o Discord fechar, ele reconecta sozinho. Um arquivo corrompido não derruba nada, e só uma cópia do programa roda por vez.

## Configuração

Clique com o botão direito no ícone da bandeja e escolha **Abrir configurações**: abre a tela de **Ajustes**, com a prévia de como o perfil fica no Discord. Tudo vale na hora, sem reiniciar. As opções ficam em `dados\config.json`; quem preferir pode editar o arquivo (botão **Abrir config.json** em Ajustes › Programa), que é recarregado sozinho quando você salva.

| Opção | Padrão | O que faz |
|---|---|---|
| `client_id` | ID do app "Guitar Rig 7" | Application ID do Discord Developer Portal |
| `language` | `"pt"` | `"pt"` ou `"en"` |
| `rotate_seconds` | `20` | Tempo entre os cartões (mínimo 15) |
| `activity_type` | `"playing"` | `playing` (Jogando), `listening` (Ouvindo), `watching`, `competing` |
| `status_display` | `"name"` | O que aparece na lista de membros: `name`, `details` ou `state` |
| `show_preset` / `show_rack_chain` / `show_tags` | `true` | Nome do preset, cadeia de efeitos, gênero e estilo |
| `show_backing_track` | `true` | Faixa aberta no Tape Deck |
| `show_stats` / `show_streak` | `true` | Cartão de prática, sequência de dias |
| `daily_goal_minutes` | `30` | Meta diária de prática, em minutos (`0` = sem meta) |
| `notify_goal` | `true` | Notificação do Windows quando a meta do dia é batida |
| `notify_minimized` | `true` | Notificação quando o Guitar Rig é minimizado (o perfil para no último preset) |
| `detect_plugin_hosts` | `true` | Procura o Guitar Rig 7 como VST3 dentro de DAWs |
| `check_updates` | `true` | Confere uma vez por dia se saiu versão nova |
| `buttons` | site do GR7 + vazio | Até 2 botões `{ "label", "url" }`. Só os outros veem os botões, você não. |

Exemplo de segundo botão: `{ "label": "Meu canal", "url": "https://youtube.com/@seucanal" }`.

## Desinstalar

Dê dois cliques em `desinstalar.bat` e depois apague a pasta.

## Solução de problemas

- **Não aparece nada.** Confira o ícone da bandeja. Cinza com "Discord não encontrado" quer dizer que o Discord desktop está fechado. Veja também o log em `dados\gr7_presence.log` (botão direito na bandeja › **Abrir pasta de dados**).
- **O preset não mudou.** Confira se o Guitar Rig não está minimizado: minimizado, ele não desenha a janela, e o perfil fica no último preset lido.
- **Imagens em branco ou ícone de dado no lugar do logo.** O Discord guarda as imagens em cache. Se uma imagem não for reconhecida, o programa passa a mandar o link direto dela sozinho. O ícone pequeno ao lado do seu nome só atualiza recarregando o Discord com **Ctrl+R**.
- **Achou um defeito?** [Abra uma issue](https://github.com/PedroMiranda243/gr7-presence/issues/new/choose) com a versão (aparece no menu da bandeja) e um trecho do log.

## Para quem desenvolve

- [`CONTRIBUTING.md`](CONTRIBUTING.md): montar o ambiente, rodar os testes, abrir um Pull Request.
- [`AGENTS.md`](AGENTS.md): regras, arquitetura e armadilhas conhecidas, para pessoas e assistentes de IA.
- [`docs/`](docs): [arquitetura](docs/arquitetura.md), [decisões](docs/decisoes.md), [como lançar uma versão](docs/lancar-versao.md) e [o app do Discord](docs/app-do-discord.md).

## Licença

[MIT](LICENSE). Projeto de fã, sem ligação com a Native Instruments. Guitar Rig é marca da Native Instruments.
