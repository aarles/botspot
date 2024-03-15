import os
import argparse
import time
import threading
import re
import sys
from  http.server import BaseHTTPRequestHandler, HTTPServer

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from mastodon import Mastodon
from odesli.Odesli import Odesli
import requests

class MastodonSpotifyBot:
    def __init__(self, args):
        self.settings = {
            "client_id": args.clientid,
            "client_secret": args.clientsecret,
            "callback_api": args.callback,
            "scope": args.scope,
            "interval": args.interval,
            "mastodon_instance": args.mastodoninstance,
            "mastodon_access_token": args.mastodonaccesstoken
        }

        if self.settings["client_id"] is None:
            self.settings["client_id"] = os.environ.get("SPOTIFY_CLIENT_ID")

        if self.settings["client_secret"] is None:
            self.settings["client_secret"] = os.environ.get("SPOTIFY_CLIENT_SECRET")

        if self.settings["mastodon_access_token"] is None:
            self.settings["mastodon_access_token"] = os.environ.get("MASTODON_ACCESS_TOKEN")

    def run(self):
        self.authenticate_spotify()
        self.authenticate_mastodon()
        last_song = None
        th = threading.Thread(target=callBackAction, args=(self.settings["callback_api"],))
        th.start()

        if not th.is_alive():
            raise Exception("Failed to start callback service")

        time.sleep(300)
        sys.exit(0)
        while True:
            dados = self.get_recently_played()
            # envia para o Mastodon
            if dados is None:
                time.sleep(self.settings["interval"])
                continue

            if last_song == dados["item"]["name"]:
                time.sleep(self.settings["interval"])
                continue

            last_song = dados["item"]["name"]
            self.mstd.toot("Ouvindo agora! \n\n" + \
                           last_song + \
                           " - " + \
                           dados["item"]["artists"][0]["name"] + \
                           " - " + \
                           self.encurta_url(str(dados["item"]["external_urls"]["spotify"])) + \
                           " \n\n " + \
                           "#JuckboxMental")

            time.sleep(self.settings["interval"])

    def authenticate_spotify(self):
        "criação do objeto de autenticação do Spotify"
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self.settings["client_id"],
                                               client_secret=self.settings["client_secret"],
                                               redirect_uri=self.settings["callback_api"],
                                               scope=self.settings["scope"]
                                                            ))

    def authenticate_mastodon(self):
        "autenticação no Mastodon"
        self.mstd = Mastodon(
            api_base_url = self.settings["mastodon_instance"],
            access_token = self.settings["mastodon_access_token"]
        )

    def get_recently_played(self) -> dict:
        "função para pegar os dados do Spotify"
        results = self.sp.current_user_playing_track()
        if results["is_playing"]:
            return results
        return None

    def encurta_url(self, url : str):
        "função para o gerenciador SongLink"
        return  Odesli().getByUrl(url).songLink


def callBackAction(localURL : str):
    "Função pra pegar o callback do spotify"
    # localURL format: http:// + localhost + : + <port> + <route>
    if not re.search("^http://localhost", localURL):
        raise Exception(f"Callback em formato errado (esperado: http://localhost:9999/rota): {localURL}")

    port_and_route = re.sub("http://localhost:", "", localURL)
    (port, route) = port_and_route.split("/")
    port = int(port)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html;charset=utf-8")
            self.end_headers()
            client_ip, client_port = self.client_address
            reqpath = self.path.rstrip()
            print(f"request from {client_ip}:{client_port} for {reqpath}")
            if reqpath == "/" + route:
                response = "some data"
            else:
                response = "Callback called"
            content = bytes(response.encode("utf-8"))
            self.wfile.write(content)

    # Bind to the local address only.
    print(f"Starting callback webserver on port {port}")
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return



if __name__ == '__main__':
    parse = argparse.ArgumentParser(description='Mastodon bot to post your spotify current listening song')
    parse.add_argument('--clientid', required=False, help='Spotify\'s client ID - it can be passed as environment variable SPOTIFY_CLIENT_ID')
    parse.add_argument('--clientsecret', required=False, help='Spotify\'s client secret - it can be passed as environment variable SPOTIFY_CLIENT_SECRET')
    parse.add_argument('--callback', required=False, default='http://localhost:8888/callback', help='Spotify\'s callback listener')
    parse.add_argument('--scope', required=False, default='user-read-currently-playing', help='Current profile?')
    parse.add_argument('--interval', required=False, default=30, type=int, help='Time to pool for next song')
    parse.add_argument('--mastodoninstance', required=False, default='https://mastodon.social', help='The instance you have an account')
    parse.add_argument('--mastodonaccesstoken', required=False, help='The token to access your mastodon account - it can be passed as environment variable MASTODON_ACCESS_TOKEN')
    args = parse.parse_args()

    bot = MastodonSpotifyBot(args)
    bot.run()
