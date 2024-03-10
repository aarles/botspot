import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from mastodon import Mastodon
from odesli.Odesli import Odesli

# criação do objeto de autenticação do Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=os.environ["SPOTIFY_CLIENT_ID"],
                                               client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
                                               redirect_uri="http://localhost:8888/callback",
                                               scope="user-read-currently-playing"))
# autenticação no Mastodon
mastodon = Mastodon(
    api_base_url = "https://mastodon.social/",
    access_token = os.environ["MASTODON_ACCESS_TOKEN"],
)

# função para o gerenciador SongLink
def encurta_url(url):
    enc = Odesli().getByUrl(url)
    link = enc.songLink
    return link

#função para pegar os dados do Spotify
def get_recently_played():
    results = sp.current_user_playing_track()
    if results["is_playing"]:
        return results
    else:
        pass


dados = get_recently_played()

# envia para o Mastodon
if dados is not None:
    mastodon.toot("Ouvindo agora! \n\n" + dados["item"]["name"] + " - " + dados["item"]["artists"][0]["name"] + " - " + encurta_url(str(dados["item"]["external_urls"]["spotify"])) + " \n\n " + "#JuckboxMental")
else:
    exit(0)
