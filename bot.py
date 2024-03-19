#! /usr/bin/env python3

## std imports
import os
import argparse
import time
import threading
import re
import sys
from  http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json

## external modules
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from mastodon import Mastodon
from odesli.Odesli import Odesli
import requests

## logging initializing
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

FIXED_INTERVAL = 60

class MastodonSpotifyBot:
    def __init__(self, args):
        self.settings = {
            "client_id": args.clientid,
            "client_secret": args.clientsecret,
            "callback_api": args.callback,
            "scope": args.scope,
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
        logger.info("Authenticating on Spotify")
        self.authenticate_spotify()
        logger.info("Authenticating on Mastodon")
        self.authenticate_mastodon()
        last_song = None
        th = threading.Thread(target=callBackAction, args=(self.settings["callback_api"],))
        th.start()

        if not th.is_alive():
            logger.error("Callback service failed to start and serve")
            raise Exception("Failed to start callback service")

        while True:
            dados = self.get_recently_played()
            logger.debug("dados: " + str(dados))
            # envia para o Mastodon
            if dados is None:
                time.sleep(FIXED_INTERVAL)
                continue

            logger.debug("dados json:\n" + json.dumps(dados, indent=4) )

            if not "is_playing" in dados:
                logger.error("Missing entry \"is_playing\"")
                time.sleep(FIXED_INTERVAL)
                continue

            if not "progress_ms" in dados:
                logger.warning("Missing entry for \"progress_ms\"")
                time.sleep(FIXED_INTERVAL)
                continue

            if dados["is_playing"] == False:
                logger.error("Spotify isn't active right now - quitting...")
                sys.exit(0)

            waiting_time_ms = int(dados["progress_ms"])
            waiting_time_seconds = waiting_time_ms / 1000.

            if dados["currently_playing_type"] != "track":
                logger.info("Not music playing: " + dados["currently_playing_type"])
                time.sleep(waiting_time_seconds)
                continue

            if last_song == dados["item"]["name"]:
                logger.warning(f"Current song is the same as last song: {last_song}")
                time.sleep(waiting_time_seconds)
                continue

            last_song = dados["item"]["name"]
            if not th.is_alive():
                logger.error("Callback server not running - exiting")
                sys.exit(1)

            logger.info(f"sending update to mastodon: {last_song}")
            self.mstd.toot("Ouvindo agora! \n\n" + \
                           last_song + \
                           " - " + \
                           dados["item"]["artists"][0]["name"] + \
                           " - " + \
                           self.encurta_url(str(dados["item"]["external_urls"]["spotify"])) + \
                           " \n\n " + \
                           "#JuckboxMental")
            logger.info(f"next song in {waiting_time_seconds} s")
            time.sleep(waiting_time_seconds)

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
        generic_response = {
                "is_playing": False,
                "progress_ms": "%d" % 1 * 60 * 1000 # 1 minute
            }

        try:
            results = self.sp.current_user_playing_track()
        except TypeError:
            return  generic_response

        if not "is_playing" in results:
            return  generic_response
        return results

    def encurta_url(self, url : str):
        "função para o gerenciador SongLink"
        return  Odesli().getByUrl(url).songLink


def callBackAction(localURL : str):
    "Função pra pegar o callback do spotify"
    # localURL format: http:// + localhost + : + <port> + <route>
    if not re.search("^http://localhost", localURL):
        logger.error("Failed to get callback URL")
        raise Exception(f"Callback em formato errado (esperado: http://localhost:9999/rota): {localURL}")

    port_and_route = re.sub("http://localhost:", "", localURL)
    (port, route) = port_and_route.split("/")
    port = int(port)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            logger.info("Callback service called")
            self.send_response(200)
            self.end_headers()
            client_ip, client_port = self.client_address
            reqpath = self.path.rstrip()
            logger.info(f"callback service: request from {client_ip}:{client_port} for {reqpath}")
            if reqpath == "/" + route:
                response = "some data"
            else:
                response = "Callback called"
            content = bytes(response.encode("utf-8"))
            self.wfile.write(content)

    # Bind to the local address only.
    logger.info(f"Starting callback webserver on port {port}")
    server_address = ('localhost', port)
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
    parse.add_argument('--mastodoninstance', required=False, default='https://mastodon.social', help='The instance you have an account')
    parse.add_argument('--mastodonaccesstoken', required=False, help='The token to access your mastodon account - it can be passed as environment variable MASTODON_ACCESS_TOKEN')
    parse.add_argument('--loglevel', default='info')
    args = parse.parse_args()

    logger.setLevel(args.loglevel.upper())

    bot = MastodonSpotifyBot(args)
    bot.run()
