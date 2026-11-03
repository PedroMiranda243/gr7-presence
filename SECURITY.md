# Segurança

## Como avisar de uma falha

Não abra uma issue pública. Use o botão **Report a vulnerability** na aba
[Security](https://github.com/PedroMiranda243/gr7-presence/security) do repositório: a conversa fica
privada entre você e quem mantém o projeto até a correção sair.

Conte o que encontrou, como reproduzir e qual versão você usa (aparece no menu da bandeja). A resposta
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
- **Escrita:** só na pasta `dados\` do programa e nos atalhos do Menu Iniciar e da Inicialização.

O programa avisa de versões novas, mas não baixa nem instala nada sozinho.
