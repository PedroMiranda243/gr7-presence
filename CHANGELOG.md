# Histórico de versões

As mudanças que quem usa percebe, da mais nova para a mais antiga. O formato segue o
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e as versões seguem o
[SemVer](https://semver.org/lang/pt-BR/): `MAIOR.MENOR.CORREÇÃO`.

O texto de cada versão vira a descrição da release no GitHub (`tools/notas_da_versao.py`). Cada Pull
Request que muda algo visível escreve aqui, em **Não lançado**.

## [Não lançado]

### Mudanças
- **Estatísticas com visual novo**, numa janela nova do GR7 Presence:
  - gráfico dos últimos 14 dias, com a luz na barra de hoje e a linha da meta, e também por semana
    (16 semanas) ou por mês;
  - conquistas: 7 e 30 dias seguidos, 10 e 100 horas, e meta batida 5 dias na mesma semana;
  - calendário dos dias tocados nas últimas 16 semanas;
  - presets, amplificadores e sessões recentes, com a sessão de agora marcada.
- **Painel**, a primeira página da janela: o preset que está tocando, em destaque, com a cadeia do
  rack; o cartão que o Discord está mostrando agora, com o tempo e quando troca para o próximo; a meta
  do dia; e se o Discord, o Guitar Rig e a leitura da tela estão funcionando. Com o Guitar Rig fechado,
  ele mostra a última sessão.
- **Pausar por 1 hora**, além de pausar até você voltar, no botão Pausar do Painel.
- **Aviso quando o Guitar Rig é minimizado.** Minimizado, ele não mostra a tela, e o perfil fica parado
  no último preset lido; agora um aviso do Windows explica isso, uma vez por vez que você abre o
  Guitar Rig. Dá para desligar nos Ajustes.
- **Tela de Ajustes**, no lugar do `config.json` aberto no Bloco de Notas. **Abrir configurações**, na
  bandeja, abre a tela com tudo o que antes só dava para mudar no arquivo, com chaves, listas e campos.
  Do lado direito, a prévia mostra na hora como o seu perfil fica no Discord e como você aparece na
  lista de membros. As mudanças valem na hora, sem reiniciar. O `config.json` continua lá para quem
  preferir (Ajustes › Programa › Abrir config.json).
- **Meta diária de prática**, de 30 minutos no começo, e um **aviso do Windows quando você bate a meta**
  do dia. Dá para mudar a meta e desligar o aviso nos Ajustes.

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

[Não lançado]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/PedroMiranda243/gr7-presence/releases/tag/v1.0.0
