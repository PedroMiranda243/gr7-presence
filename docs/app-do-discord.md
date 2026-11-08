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
   `gr7_logo`, `amp`, `pedal`, `tape`, `clock`, `fire`, `daw`, `trophy`. O Discord leva alguns minutos
   para reconhecer imagens novas.
5. Ponha o ID no `client_id` do `dados\config.json` para testar. Para valer para todo mundo, troque o
   padrão em `gr7_presence/config.py` num PR e publique uma versão.

## Imagem nova numa versão

Quando uma versão traz um ícone novo, ele precisa ir para o app que já existe; não é preciso refazer o
app. Na 1.5.0, é o `trophy`, do cartão "🏆 Conquista: …":

1. No Developer Portal, abra o app **Guitar Rig 7** › **Rich Presence › Art Assets**.
2. Envie `assets\discord	rophy.png` com o nome `trophy` (o arquivo já está no repositório; não precisa
   do Guitar Rig).
3. Faça isso antes de publicar a versão. Até o Discord reconhecer a imagem, o cartão da conquista
   aparece sem o ícone pequeno; o texto e os outros cartões não mudam.

## Imagens em branco depois de trocar

O Discord guarda em cache a lista de imagens do app. Enquanto ele não reconhece uma chave, o
`assets.py` passa a mandar o link direto do CDN (`cdn.discordapp.com/app-assets/<app>/<imagem>.png`).
O ícone ao lado do nome, no painel de usuário, só atualiza recarregando o Discord com **Ctrl+R**.
