import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from mastodon import Mastodon
from odesli.Odesli import Odesli


sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=os.environ["SPOTIFY_CLIENT_ID"],
                                               client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
                                               redirect_uri="http://localhost:8888/callback",
                                               scope="user-read-currently-playing"))

mastodon = Mastodon(
    api_base_url = "https://mastodon.social/",
    access_token = os.environ["MASTODON_ACCESS_TOKEN"],
)


def encurta_url(url):
    enc = Odesli().getByUrl(url)
    link = enc.songLink
    return link


def get_recently_played():
    results = sp.current_user_playing_track()
    if results["is_playing"]:
        return results
    else:
        pass


dados = get_recently_played()

if dados is not None:
    mastodon.toot("Ouvindo agora! \n" +dados["item"]["name"] + " - " + dados["item"]["artists"][0]["name"] + " - " + encurta_url(str(dados["item"]["external_urls"]["spotify"])) + " \n " + "#JuckboxMental")
else:
    exit(0)
