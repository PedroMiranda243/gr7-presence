# Decisões de arquitetura

Cada decisão com a situação, o que foi escolhido, as alternativas e o preço. Decisão nova entra no
fim, com o próximo número. Decisão que muda ganha um **adendo** com a data, em vez de ser apagada: o
motivo antigo explica o código antigo.

---

## D1. Cliente próprio para o pipe do Discord

**Situação.** O Rich Presence fala com o Discord desktop por um *named pipe* local
(`\\?\pipe\discord-ipc-N`), com quadros `<op u32><tamanho u32><JSON>`.

**Decisão.** Um cliente próprio (`discord_ipc.py`), em vez do `pypresence`.

**Por quê.** Controle dos campos novos (`type`, `status_display_type`, botões), da reconexão e dos
erros, sem depender do ritmo de outra biblioteca. O protocolo cabe em ~150 linhas.

**Preço.** Somos donos do protocolo: quando o Discord mudar, a correção é nossa. A leitura não pode
ficar pendurada numa thread (o pipe é síncrono e serializa leitura e escrita); usamos `PeekNamedPipe`.

## D2. Preset ao vivo por captura da janela e OCR do Windows

**Situação.** O Guitar Rig não tem API. O `LastEditBuffer.tle` só é gravado ao fechar, o título da
janela é sempre "Guitar Rig 7", e a interface Qt/QML não expõe o nome do preset para a acessibilidade.

**Decisão.** Capturar a janela com `PrintWindow` (funciona com ela atrás de outras), ler o topo com o
OCR nativo do Windows (`winrt`) e casar o texto com a biblioteca de presets, tolerando os erros típicos
do OCR.

**Alternativas.** Ler a memória do processo (frágil a cada atualização, e invasivo); observar o
arquivo (só muda ao fechar); pedir à pessoa que digite o preset (ninguém faria).

**Preço.** Minimizada, a janela não é desenhada, e fica o último preset lido. Sem os pacotes `winrt`, o
programa funciona só com o preset da abertura. O OCR custa pouco: uma captura a cada 5 segundos.

## D3. Dados na pasta do programa, não em `%APPDATA%`

**Situação.** O programa aberto pelo assistente (de dentro do app desktop do Claude, um pacote MSIX) e
o aberto pela pessoa liam `%APPDATA%` diferentes, porque o Windows redireciona o `AppData` de apps
empacotados. Resultado: "abro e não acontece nada".

**Decisão.** `dados\` dentro da pasta do programa. O `migrate.py` traz o que estava nos lugares antigos
na primeira abertura.

**Preço.** A pasta do programa precisa ser gravável (por isso o guia manda extrair em Documentos, e não
em Arquivos de Programas), e a atualização não pode apagar `dados\`.

## D4. Um app do Discord para todo mundo

**Decisão.** O Application ID do app "Guitar Rig 7" vem embutido no `config.py`. Quem instala não cria
nada no Developer Portal.

**Preço.** Se o app for apagado da conta de quem o criou, o programa para de funcionar para todos. As
imagens do perfil vivem nesse app. Como refazê-lo: [`app-do-discord.md`](app-do-discord.md).

## D5. A arte da Native Instruments fica fora do repositório

**Situação.** O logo do Guitar Rig é marca registrada da Native Instruments, e o repositório é público.

**Decisão.** O `tools/make_assets.py --locais` extrai o ícone do `Guitar Rig 7.exe` de quem instala,
durante a instalação. O `.gitignore` bloqueia esses arquivos, e o zip só leva arquivos versionados. Os
ícones pequenos (amp, pedal, fita…) são desenhados pelo próprio projeto e ficam versionados.

**Preço.** Sem o Guitar Rig no caminho padrão, a bandeja usa um círculo laranja.

## D6. Distribuição como zip com instalador, não como executável

**Decisão.** Um zip com o código, um `instalar.bat` que cria o ambiente Python e instala as
dependências.

**Por quê.** Atualizações pequenas (~300 KB), código que quem usa pode ler, e nenhum executável
empacotado, do tipo que antivírus costumam marcar como suspeito.

**Preço.** Precisa de Python. O instalador oferece instalar o 3.11 pelo `winget`, com confirmação.

## D7. Aviso de versão nova, sem atualização automática

**Situação.** Quem usa precisa saber que saiu versão nova sem ficar olhando o GitHub.

**Decisão.** Uma consulta por dia à API pública de releases (`updates.py`). Achou versão maior: uma
notificação e um item no menu que abre a página da release. Quem usa baixa e instala.

**Alternativas.** Atualização automática (baixar e substituir os arquivos sozinho). Fica para depois:
código que se substitui sozinho precisa de verificação de integridade e de um caminho de volta, e um
erro ali quebra a instalação de todo mundo de uma vez.

**Preço.** A atualização tem três passos manuais (sair, extrair por cima, rodar o instalador).

**Adendo (2026-11-03): atualização com um clique.** O item do menu abre uma janela com o que muda e o
botão "Atualizar agora". As duas condições acima foram atendidas assim:

- **Integridade.** O zip só é baixado de uma release deste repositório e precisa bater com o sha256
  que a API do GitHub informa para o anexo. Não bateu, é apagado; nada é extraído.
- **Caminho de volta.** O `tools/atualizar.py` guarda os arquivos que vai trocar em
  `dados\atualizacao\anterior` antes de extrair. Se o instalador falhar (ou qualquer outro passo), devolve
  esses arquivos, apaga os que a versão nova criou e reabre a versão anterior.
- **Quem troca os arquivos é o atualizador da versão instalada**, copiado para a pasta temporária, e não o
  que vem no zip: um zip defeituoso não decide como ele mesmo é instalado.
- **O atualizador espera o programa fechar e usa só a biblioteca padrão.** Enquanto o programa roda, os
  `.pyd` do `psutil` e do `Pillow` ficam presos e o `pip` não consegue atualizá-los.
- **Nunca toca em `dados\` nem em `.venv\`**; um zip com caminho fora do lugar é recusado inteiro.

Testado de ponta a ponta numa cópia instalada, com um servidor local no papel do GitHub: 1.0.0 → 1.1.0
instalou e reabriu; 1.1.0 → 1.2.0 com o instalador quebrado de propósito voltou sozinho para a 1.1.0.

**Preço que fica.** O `pip` pode ter atualizado dependências antes da falha, e elas não voltam (o código
antigo continua funcionando com versões mais novas das mesmas bibliotecas). Arquivos que uma versão
nova deixou de usar não são apagados, como acontecia ao extrair o zip por cima.

## D8. Testes com arquivos sintéticos

**Situação.** Os primeiros testes usavam um `LastEditBuffer.tle` real e um preset de fábrica da Native
Instruments, que não podem ir para um repositório público.

**Decisão.** `tests/sinteticos.py` gera `.tle` e `.ngrr` com dados inventados. O
`test_instalacao_real.py` confere o leitor contra os presets de fábrica de verdade e é pulado onde o
Guitar Rig não está instalado (como na CI).

**Preço.** A CI não vê arquivos reais. Antes de uma release, rode os testes numa máquina com o Guitar
Rig.
