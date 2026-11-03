# O app do Discord

O perfil mostra "Jogando **Guitar Rig 7**" porque existe um aplicativo com esse nome no
[Discord Developer Portal](https://discord.com/developers/applications). O Application ID dele vem
embutido no `gr7_presence/config.py` (decisão D4), e as imagens do perfil são guardadas nele.

Só é preciso refazê-lo se o app atual for apagado, ou para testar com outro app.

## Criar

1. Gere as imagens. Com o Guitar Rig 7 instalado, rode
   `.venv\Scripts\python tools\make_assets.py`. Saem em `assets\discord\` (as tiradas do Guitar Rig
   ficam só no seu PC) e uma folha de conferência em `assets\preview.png`.
2. No Developer Portal, **New Application**, com o nome **Guitar Rig 7**. Esse nome aparece no perfil.
3. Em **General Information**, envie `assets\discord\app_icon.png` como ícone e copie o
   **Application ID**.
4. Em **Rich Presence › Art Assets**, envie as imagens de `assets\discord\` mantendo os nomes:
   `gr7_logo`, `amp`, `pedal`, `tape`, `clock`, `fire`, `daw`. O Discord leva alguns minutos para
   reconhecer imagens novas.
5. Ponha o ID no `client_id` do `dados\config.json` para testar. Para valer para todo mundo, troque o
   padrão em `gr7_presence/config.py` num PR e publique uma versão.

## Imagens em branco depois de trocar

O Discord guarda em cache a lista de imagens do app. Enquanto ele não reconhece uma chave, o
`assets.py` passa a mandar o link direto do CDN (`cdn.discordapp.com/app-assets/<app>/<imagem>.png`).
O ícone ao lado do nome, no painel de usuário, só atualiza recarregando o Discord com **Ctrl+R**.
