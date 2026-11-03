# Lançar uma versão

Uma versão é uma tag `vX.Y.Z` na `main`. A tag dispara o workflow **Release**, que testa, confere a
versão, gera o zip e publica a release. Quem usa recebe o aviso na bandeja em até um dia.

## Que número usar

`MAIOR.MENOR.CORREÇÃO` ([SemVer](https://semver.org/lang/pt-BR/)):

| Mudou | Sobe | Exemplo |
|---|---|---|
| Só correção, nada novo para quem usa | CORREÇÃO | 1.0.0 → 1.0.1 |
| Recurso novo, tudo que existia continua igual | MENOR | 1.0.1 → 1.1.0 |
| Quem atualiza precisa fazer algo diferente (config incompatível, Python mínimo maior) | MAIOR | 1.1.0 → 2.0.0 |

## O roteiro

1. **Confira a `main`.** Tudo que vai na versão já foi mesclado, a CI está verde, e o `CHANGELOG.md`
   tem as mudanças em *Não lançado*. Rode os testes numa máquina com o Guitar Rig 7: os de instalação
   real não rodam na CI.
2. **PR de versão** (ramo `chore/versao-X.Y.Z`):
   - `gr7_presence/__init__.py`: `__version__ = "X.Y.Z"`;
   - `CHANGELOG.md`: *Não lançado* vira `## [X.Y.Z] - AAAA-MM-DD`, uma seção *Não lançado* vazia volta
     ao topo, e os links do fim ganham a versão nova.
3. **Depois do merge, a tag:**

   ```bash
   git switch main
   git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

4. **Acompanhe o workflow** em Actions › Release. Ele falha, sem publicar nada, se:
   - a tag não bate com `__version__` ou falta a seção no `CHANGELOG.md`;
   - algum teste falha;
   - o empacotador acha dado pessoal, ou o secret `GR7_PALAVRAS_PRIVADAS` está vazio.
5. **Confira a release:** abra a página, baixe o zip pelo link do README e veja se ele abre com a pasta
   `GR7 Presence` e o `COMO INSTALAR.txt`.

## Se algo der errado

- **O workflow falhou antes de publicar:** corrija num PR, apague a tag (`git push origin :vX.Y.Z` e
  `git tag -d vX.Y.Z`) e recomece do passo 3.
- **Saiu uma versão com defeito:** não apague a release (quem já baixou fica sem referência). Publique a
  correção como `X.Y.Z+1` pelo mesmo roteiro.

## O secret das palavras privadas

O `tools/empacotar.py` procura nos arquivos versionados as palavras de uma lista que não pode estar no
repositório (nomes de contas, partes de e-mail). Na CI ela vem do secret `GR7_PALAVRAS_PRIVADAS`
(palavras separadas por vírgula); no PC de quem publica, de `dados\palavras-privadas.txt` (uma por
linha). Para trocar o secret sem mostrar as palavras na tela:

```bash
gh secret set GR7_PALAVRAS_PRIVADAS < arquivo-com-as-palavras.txt
```
