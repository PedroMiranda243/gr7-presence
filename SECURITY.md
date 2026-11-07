# Segurança

## Como avisar de uma falha

Não abra uma issue pública. Use o botão **Report a vulnerability** na aba
[Security](https://github.com/PedroMiranda243/gr7-presence/security) do repositório: a conversa fica
privada entre você e quem mantém o projeto até a correção sair.

Conte o que encontrou, como reproduzir e qual versão você usa (aparece em Ajustes › Programa). A resposta
pode levar alguns dias: é um projeto mantido no tempo livre.

## O que o programa faz de sensível

Para avaliar o risco, é isto que o GR7 Presence faz no seu PC:

- **Instalação:** o `instalar.bat` roda o `tools\instalar.ps1`, que cria um ambiente Python na pasta do
  programa e instala os pacotes do `requirements.txt` pelo `pip`. Se faltar Python, oferece instalá-lo
  pelo `winget`, só com a sua confirmação.
- **Leitura local:** o processo do Guitar Rig 7, a janela dele (captura para o OCR do Windows), os
  presets nas pastas do Guitar Rig e os arquivos de áudio abertos no Tape Deck (só o nome).
- **Rede:** o pipe local do Discord (no seu PC), a lista pública de imagens do app no Discord e, uma
  vez por dia, a página pública da última release no GitHub. Nada do que você toca sai do seu PC, a
  não ser o que o Discord mostra no seu perfil.
- **Escrita:** só na pasta do programa (`dados\` e, numa atualização, os arquivos do programa), numa
  pasta temporária `GR7 Presence atualizacao` e nos atalhos do Menu Iniciar e da Inicialização.

**Atualizações.** O programa só atualiza quando você clica em "Atualizar agora". O zip vem do anexo de
uma release deste repositório (link de outro lugar é recusado) e precisa bater com o sha256 que a API do
GitHub informa para ele; se não bater, é apagado sem ser usado. Quem troca os arquivos é o
`tools\atualizar.py` da versão já instalada, que guarda uma cópia dos arquivos antigos, recusa qualquer
caminho fora da pasta do programa, não toca em `dados\` nem em `.venv\` e devolve a versão anterior se
algo falhar. O registro de cada atualização fica em `dados\atualizacao.log`.
