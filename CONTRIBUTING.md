# Como contribuir

Obrigado pelo interesse! O GR7 Presence é um projeto pequeno, de fã, mantido no tempo livre. Antes de
mexer no código, leia o [`AGENTS.md`](AGENTS.md): ele tem as regras, a arquitetura e as armadilhas que
já custaram tempo.

## Achou um problema ou tem uma ideia?

Abra uma [issue](https://github.com/PedroMiranda243/gr7-presence/issues/new/choose) pelo modelo. Para
problemas, a versão do GR7 Presence (aparece no menu da bandeja) e um trecho do
`dados\gr7_presence.log` ajudam muito. Apague do log o que você não quiser mostrar, como nomes de
presets ou de faixas.

Falha de segurança não vai em issue pública: veja o [`SECURITY.md`](SECURITY.md).

## Montando o ambiente

Precisa de Windows 10 ou 11, Python 3.10 a 3.13 (de preferência o 3.11) e, para testar de verdade, o
Guitar Rig 7 e o Discord desktop.

```bash
git clone https://github.com/PedroMiranda243/gr7-presence.git
cd gr7-presence
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-ocr.txt
.venv\Scripts\python -m unittest discover -s tests -t .
```

O ícone do programa (`assets\gr7_presence.ico` e `.png`, o selo vermelho com o pedal) já vem no
repositório e sai da arte em `assets\gr7_presence_fonte.png`. Para trocar a arte, rode
`.venv\Scripts\python tools\make_assets.py --icone-de arte-nova.png`: uma arte com fundo branco tem o
círculo recortado sozinho. Confira os tamanhos pequenos (16 a 32 px) antes do PR.

Os testes usam arquivos sintéticos (`tests/sinteticos.py`). Os de `tests/test_instalacao_real.py` leem
os presets de fábrica do seu Guitar Rig e são pulados onde ele não está instalado, como na CI.

## Do ramo ao merge

1. Uma issue por mudança, com o que se espera. Se a regra não está escrita, pergunte na issue.
2. Ramo a partir da `main` atualizada: `git switch main && git pull && git switch -c fix/descricao-curta`.
3. Mudança pequena e no escopo. O que estiver errado fora dele vira outra issue.
4. Teste junto com o comportamento novo. Mudou algo visível? Escreva no `CHANGELOG.md`, em *Não lançado*.
5. Commits no formato `tipo: efeito`, explicando o porquê no corpo:

   ```
   fix: preset com nome cortado aparece completo

   O Guitar Rig corta nomes longos com "..." e o OCR lê o texto cortado. O casamento
   por prefixo acha o preset certo e recusa quando vários começam igual.

   Refs #12
   ```

6. Pull Request pelo modelo, com `Closes #N` (em inglês: o GitHub ignora "Fecha #N").
7. A CI roda os testes no Windows (Python 3.10, 3.11 e 3.13) e procura dados pessoais. Com tudo verde,
   o merge é por **squash**: um commit por PR na `main`, com o título do PR.

Commits não levam coautoria de assistente de IA nem menção à ferramenta (regra 2 do `AGENTS.md`).

## Publicando uma versão

Só quem mantém o repositório publica, seguindo o [`docs/lancar-versao.md`](docs/lancar-versao.md). Em
resumo: a versão sobe num PR, a tag `vX.Y.Z` vai para a `main`, e a CI testa, gera o zip e publica a
release. Quem usa recebe o aviso em até um dia.
