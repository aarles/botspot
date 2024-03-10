# Introdução

Este script tem a finalidade de integrar a API do Spotify com a API de Mastodon, passando pelo agregador de URLs SoundLink.

### Chaves de API

As chaves de API do Spotify devem ser conseguidas na página: https://developers.spotyfy.com

O Token do Mastodon é encontrado na página de desenvolvimento das configurações da Plataforma.

### Instalação

Criar um Venv:

$ python3 -m venv .venv

$ source .venv/bin/activate

Instalar as libs:

$ pip3 install -r requirements.txt

### Rodar o sistema

Para rodar o sistema, exportar as variáveis como variáveis de ambiente do SO:

$ export SPOTIFY_CLIENT_ID='chave_aqui'

$ export SPOTIFY_CLIENT_SECRET='chave_aqui'

$ export MASTODON_ACCESS_TOKEN='token_aqui'

Após isso, basta colocar o Cron Job para rodar num intervalo de tempo determinado.

$ crontab -e

*/15 * * * * cd /path-to-script/ && .venv/bin/python3 bot.py




