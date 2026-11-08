# Histórico de versões

As mudanças que quem usa percebe, da mais nova para a mais antiga. O formato segue o
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e as versões seguem o
[SemVer](https://semver.org/lang/pt-BR/): `MAIOR.MENOR.CORREÇÃO`.

O texto de cada versão vira a descrição da release no GitHub (`tools/notas_da_versao.py`). Cada Pull
Request que muda algo visível escreve aqui, em **Não lançado**.

## [Não lançado]

## [1.4.3] - 2026-11-07

### Como atualizar
- **Da 1.1.0 em diante:** botão direito no ícone da bandeja › **⬆️ Atualizar para a versão 1.4.3** ›
  **Atualizar agora**.
- **Da 1.0.0 ou de antes:** à mão. Botão direito na bandeja › **Sair**, extraia o zip **na mesma
  pasta**, substituindo os arquivos, e rode o `instalar.bat`.
- **Vindo da 1.3.1 ou de antes,** esta versão traz também a interface nova da 1.4.0: uma janela só,
  com Painel, Estatísticas, Ajustes e Atualização, meta diária de prática, pausa de 1 hora, aviso de
  Guitar Rig minimizado e a primeira abertura. Suas estatísticas e opções continuam: elas ficam na
  pasta `dados`, que a atualização não toca.

### Mudanças
- **Estatísticas: a linha da meta passa na frente das barras,** em vez de sumir atrás delas.
- **Estatísticas: o tempo total mostra horas e minutos** ("13 h 12 min"), como o dos últimos 7 dias. Antes
  aparecia só "13 h".

### Correções
- **As listas de opções fecham com um clique fora delas.** A lista do tipo de atividade (Jogando,
  Ouvindo…) nos Ajustes e a do **Pausar** no Painel só fechavam escolhendo uma opção. Agora um clique
  em qualquer outro ponto da janela fecha a lista sem mudar nada.

## [1.4.2] - 2026-11-07

### Como atualizar
- **Da 1.1.0 em diante:** botão direito no ícone da bandeja › **⬆️ Atualizar para a versão 1.4.2** ›
  **Atualizar agora**.
- **Da 1.0.0 ou de antes:** à mão. Botão direito na bandeja › **Sair**, extraia o zip **na mesma
  pasta**, substituindo os arquivos, e rode o `instalar.bat`.
- **Vindo da 1.3.1 ou de antes,** esta versão traz também a interface nova da 1.4.0: uma janela só,
  com Painel, Estatísticas, Ajustes e Atualização, meta diária de prática, pausa de 1 hora, aviso de
  Guitar Rig minimizado e a primeira abertura. Suas estatísticas e opções continuam: elas ficam na
  pasta `dados`, que a atualização não toca.

### Correções
- **Estatísticas sem espaço vazio em janela mais larga.** O calendário dos dias tocados mostra mais
  semanas até preencher o painel, e as barras de presets e amplificadores crescem até o tempo, em vez
  de sobrar espaço vazio.

## [1.4.1] - 2026-11-07

### Como atualizar
- **Da 1.1.0 em diante:** botão direito no ícone da bandeja › **⬆️ Atualizar para a versão 1.4.1** ›
  **Atualizar agora**.
- **Da 1.0.0 ou de antes:** à mão. Botão direito na bandeja › **Sair**, extraia o zip **na mesma
  pasta**, substituindo os arquivos, e rode o `instalar.bat`.
- **Vindo da 1.3.1 ou de antes,** esta versão traz também a interface nova da 1.4.0: uma janela só,
  com Painel, Estatísticas, Ajustes e Atualização, meta diária de prática, pausa de 1 hora, aviso de
  Guitar Rig minimizado e a primeira abertura. Suas estatísticas e opções continuam: elas ficam na
  pasta `dados`, que a atualização não toca.

### Correções
- **Os títulos e os números grandes voltam à fonte Archivo**, a dos exemplos aprovados. O zip da 1.4.0
  saiu sem a fonte, e a janela usava a Segoe UI no lugar.

## [1.4.0] - 2026-11-07

### Como atualizar
- **Da 1.1.0 em diante:** botão direito no ícone da bandeja › **⬆️ Atualizar para a versão 1.4.0** ›
  **Atualizar agora**.
- **Da 1.0.0 ou de antes:** à mão. Botão direito na bandeja › **Sair**, extraia o zip **na mesma
  pasta**, substituindo os arquivos, e rode o `instalar.bat`.
- Suas estatísticas e opções continuam: elas ficam na pasta `dados`, que a atualização não toca.

### Mudanças
- **Interface nova, numa janela só.** O GR7 Presence ganhou uma janela escura, com uma barra lateral e
  quatro páginas: Painel, Estatísticas, Ajustes e Atualização. **Abrir o GR7 Presence**, no menu da
  bandeja (ou um clique no ícone), abre a janela.
- **Painel:** o preset que está tocando, em destaque, com a cadeia do rack; o cartão que o Discord está
  mostrando agora, com o tempo e quando troca para o próximo; a meta do dia; e se o Discord, o Guitar
  Rig e a leitura da tela estão funcionando. Com o Guitar Rig fechado, ele mostra a última sessão.
- **Estatísticas com visual novo:** gráfico dos últimos 14 dias, com a luz na barra de hoje e a linha da
  meta, e também por semana (16 semanas) ou por mês; calendário dos dias tocados nas últimas 16
  semanas; presets, amplificadores e sessões recentes, com a sessão de agora marcada.
- **Conquistas:** 7 e 30 dias seguidos, 10 e 100 horas, e meta batida 5 dias na mesma semana.
- **Ajustes, no lugar do `config.json` no Bloco de Notas.** Tudo o que antes só dava para mudar no
  arquivo, com chaves, listas e campos. Do lado direito, a prévia mostra na hora como o seu perfil fica
  no Discord e como você aparece na lista de membros. As mudanças valem na hora, sem reiniciar. O
  `config.json` continua lá para quem preferir (Ajustes › Programa › Abrir config.json).
- **Meta diária de prática**, de 30 minutos no começo, e um **aviso do Windows quando você bate a
  meta** do dia.
- **Aviso quando o Guitar Rig é minimizado.** Minimizado, ele não mostra a tela, e o perfil fica parado
  no último preset lido; o aviso explica isso, uma vez por vez que você abre o Guitar Rig. Os dois
  avisos podem ser desligados nos Ajustes.
- **Pausar por 1 hora**, além de pausar até você voltar, no menu da bandeja e no Painel.
- **Menu da bandeja mais curto:** abrir a janela, pausar, atualizar quando sai versão nova e sair. A
  versão instalada, os registros e "Iniciar com o Windows" agora ficam em Ajustes › Programa.
- **Atualização dentro da janela**, com o que muda, o andamento do download e como funciona.
- **Primeira abertura:** na primeira vez, uma janela confere se o Discord, o Guitar Rig e a leitura da
  tela estão prontos, mostra como o perfil vai ficar e pergunta a meta diária e se o programa inicia
  com o Windows. Quem atualiza também vê essa janela, uma vez.
- **A janela funciona pelo teclado:** Tab e Shift+Tab andam pelos botões e chaves, Enter ou espaço
  acionam e as setas mexem no tempo de troca do cartão. Um contorno âmbar mostra onde você está.

## [1.3.1] - 2026-11-03

### Como atualizar
- **Da 1.1.0 em diante:** botão direito no ícone da bandeja › **⬆️ Atualizar para a versão 1.3.1** ›
  **Atualizar agora**.
- **Da 1.0.0 ou de antes:** à mão. Botão direito na bandeja › **Sair**, extraia o zip **na mesma
  pasta**, substituindo os arquivos, e rode o `instalar.bat`.

### Mudanças
- **O ícone volta a ser o pedal vermelho visto de cima**, o mesmo da 1.2.0, no lugar do selo da 1.3.0.
  A correção do aviso de versão nova continua.

## [1.3.0] - 2026-11-03

### Como atualizar
- **Da 1.1.0 ou da 1.2.0:** botão direito no ícone da bandeja › **⬆️ Atualizar para a versão 1.3.0** ›
  **Atualizar agora**. O programa fecha, instala e abre de novo sozinho.
- **Da 1.0.0 ou de antes:** à mão. Botão direito na bandeja › **Sair**, extraia o zip **na mesma
  pasta**, substituindo os arquivos, e rode o `instalar.bat`.

### Mudanças
- **Ícone novo: um selo vermelho com um pedal de expressão branco.** Ele fica mais fácil de reconhecer
  na barra de tarefas do que o pedal visto de cima da 1.2.0. Nos tamanhos pequenos, o pedal aparece
  ampliado dentro do selo.

### Correções
- O aviso "Saiu a versão X" não aparecia quando a versão nova era encontrada logo ao abrir o programa:
  ele era disparado antes de a bandeja estar pronta. Agora ele espera a bandeja e aparece.

## [1.2.0] - 2026-11-03

### Como atualizar
- **Da 1.1.0:** botão direito no ícone da bandeja › **⬆️ Atualizar para a versão 1.2.0** › **Atualizar
  agora**. O programa fecha, instala e abre de novo sozinho.
- **Da 1.0.0 ou de antes:** à mão. Botão direito na bandeja › **Sair**, extraia o zip **na mesma
  pasta**, substituindo os arquivos, e rode o `instalar.bat`.

### Mudanças
- **Ícone próprio: um pedal de expressão vermelho.** Ele aparece na bandeja, na barra de tarefas, nas
  janelas e nos atalhos do Menu Iniciar e da Inicialização, no lugar do logo do Guitar Rig, para não
  confundir os dois programas abertos ao mesmo tempo. O perfil do Discord continua com o logo do
  Guitar Rig 7.
- A barra de tarefas não mostra mais o ícone do Python quando uma janela do programa está aberta.
- Quem atualiza pelo botão ganha os atalhos com o ícone novo automaticamente.

## [1.1.0] - 2026-11-03

### Como atualizar vindo da 1.0.0
A 1.0.0 ainda não tem o botão, então esta atualização é à mão: botão direito no ícone da bandeja ›
**Sair**, extraia o zip **na mesma pasta**, substituindo os arquivos, e rode o `instalar.bat`. Da
próxima versão em diante, é um clique.

### Novidades
- **Atualização com um clique.** O item "⬆️ Atualizar para a versão X" da bandeja abre uma janela com o
  que muda na versão nova. Em "Atualizar agora", o programa baixa a versão, confere se o arquivo é o
  mesmo publicado no GitHub, fecha, instala e abre de novo sozinho. Se algo der errado, a versão
  anterior volta, e o motivo fica em `dados\atualizacao.log`.
- Depois de uma atualização, uma notificação avisa que deu certo (ou que a versão anterior foi mantida).

## [1.0.0] - 2026-11-03

Primeira versão publicada no GitHub.

### Novidades
- **Aviso de versão nova.** Ao abrir e depois uma vez por dia, o programa confere as releases do
  GitHub. Quando sai uma versão nova, aparece uma notificação e o item "⬆️ Baixar a versão X" no menu
  da bandeja. Dá para desligar com `"check_updates": false` no `config.json`.
- O menu da bandeja mostra a versão instalada.

### Correções em relação ao zip compartilhado em 26/10
- Presets do usuário: o programa procurava na pasta errada e agora usa
  `Documentos\Native Instruments\User Content\Guitar Rig 7`.
- Nomes longos que o Guitar Rig corta com "..." aparecem completos no perfil.
- "Split B" não aparece mais como efeito na cadeia.

### Mudanças
- O ícone oficial do Guitar Rig deixou de vir no zip, porque é arte da Native Instruments. O
  instalador copia o ícone do Guitar Rig instalado no seu PC.

[Não lançado]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.4.3...HEAD
[1.4.3]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.4.2...v1.4.3
[1.4.2]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.4.1...v1.4.2
[1.4.1]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/PedroMiranda243/gr7-presence/releases/tag/v1.0.0
