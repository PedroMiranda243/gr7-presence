# Histórico de versões

As mudanças que quem usa percebe, da mais nova para a mais antiga. O formato segue o
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e as versões seguem o
[SemVer](https://semver.org/lang/pt-BR/): `MAIOR.MENOR.CORREÇÃO`.

O texto de cada versão vira a descrição da release no GitHub (`tools/notas_da_versao.py`). Cada Pull
Request que muda algo visível escreve aqui, em **Não lançado**.

## [Não lançado]

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

[Não lançado]: https://github.com/PedroMiranda243/gr7-presence/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/PedroMiranda243/gr7-presence/releases/tag/v1.0.0
