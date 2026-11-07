# Product

<!-- impeccable:product-schema 1 -->

## Platform

windows

Programa de bandeja para Windows 10 e 11, em Python. As janelas são Tkinter, com o visual desenhado em
imagens pelo Pillow (decisão do dono do projeto em 2026-11-07: nenhuma dependência nova para a interface).

## Users

Músicos que tocam guitarra ou baixo no Guitar Rig 7 (Native Instruments), em casa, e usam o Discord.
Não são programadores: baixam um zip da página de releases, rodam o `instalar.bat` e esperam que
funcione sem mexer em nada. Abrem as janelas do programa entre uma música e outra, com o Guitar Rig
aberto ao lado.

## Product Purpose

Mostrar no perfil do Discord o que a pessoa está tocando no Guitar Rig 7 (preset, amplificador, cadeia
de efeitos, faixa do Tape Deck, tempo de uso) e guardar estatísticas de prática. Sucesso: a pessoa liga
o computador, abre o Guitar Rig e o perfil se atualiza sozinho; quando quer, vê quanto praticou.

## Positioning

O Guitar Rig não tem API. O programa descobre o estado de fora: lê a janela por OCR do Windows e confere
o nome contra a biblioteca de presets. Nenhum outro programa mostra o preset ao vivo no Discord.

## Operating Context

- Ícone na bandeja com um menu curto (abrir, pausar, atualizar, sair) e uma janela com Painel,
  Estatísticas, Ajustes e Atualização. Na primeira abertura, uma janela de boas-vindas.
- As configurações hoje são um `config.json` aberto no Bloco de Notas.
- Notificações do Windows avisam versão nova e atualização concluída.
- O Guitar Rig 7 e o Discord ficam abertos ao mesmo tempo, os dois com interface escura.

## Capabilities and Constraints

- Limites do Discord: troca de cartão a cada 15 s ou mais, textos de 2 a 128 caracteres, rótulo de
  botão até 32.
- Dados de cada sessão de prática: início, duração, preset e amp mais usados, programa (Guitar Rig ou
  DAW).
- Textos da interface em português e inglês.
- O programa é DPI aware: tudo precisa escalar com a escala do Windows.
- Python 3.10 a 3.13; dependência nova só com motivo, licença permissiva e wheel para Windows.

## Brand Commitments

- Nome: GR7 Presence. Ícone: um pedal de expressão vermelho (`#E0141C`) visto de cima.
- Não pode ser confundido com o próprio Guitar Rig 7 quando os dois estão abertos.
- Nenhuma arte, logo ou marca da Native Instruments na interface do programa.

## Evidence on Hand

- Ícone em `assets/gr7_presence.ico` e `assets/gr7_presence.png`.
- Nenhum depoimento, número de usuários ou captura pública: nada disso pode ser inventado.

## Product Principles

1. Funciona sem mexer em nada; configurar é opcional e nunca exige editar arquivo.
2. Quem usa não vê erro técnico: o que deu errado aparece em palavras simples, com o que fazer.
3. O perfil do Discord é o produto; a interface do programa explica e controla o que aparece lá.
4. Praticar é o motivo de abrir o Guitar Rig; as estatísticas incentivam sem cobrar.
