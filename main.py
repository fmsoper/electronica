import logging
import os
import sys

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyOauthError
from googleapiclient.discovery import build

import config
import utils

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = [
    "YT_API_KEY",
    "SP_CLIENT_ID",
    "SP_CLIENT_SECRET",
    "REFRESH_TOKEN",
    "REDIRECT_URI",
    "SP_USERNAME",
    "PLAYLIST_ID",
]

def load_credentials() -> dict:
    return {key: os.environ[key] for key in REQUIRED_ENV_VARS}


def build_spotify_client(creds: dict) -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=creds["SP_CLIENT_ID"],
        client_secret=creds["SP_CLIENT_SECRET"],
        redirect_uri=creds["REDIRECT_URI"],
        scope="playlist-modify-public",
    )

    try:
        token_info = auth_manager.refresh_access_token(creds["REFRESH_TOKEN"])
    except SpotifyOauthError as e:
        if "invalid_grant" in str(e) or "Refresh token expired" in str(e):
            logger.error(
                "\n----------------------------------------------------------------\n"
                "SPOTIFY REFRESH TOKEN HAS EXPIRED\n"
                "As of July 2026, Spotify refresh tokens expire after 6 months.\n"
                "You need to re-authorize this app and update the REFRESH_TOKEN\n"
                "GitHub secret. Run get_refresh_token.py locally to generate a\n"
                "new one, then update it at:\n"
                "  Settings -> Secrets and variables -> Actions -> REFRESH_TOKEN\n"
                "----------------------------------------------------------------\n"
            )
            sys.exit(1)
        raise

    return spotipy.Spotify(auth=token_info["access_token"])


def main():
    creds = load_credentials()

    youtube = build("youtube", "v3", developerKey=creds["YT_API_KEY"])
    sp = build_spotify_client(creds)

    logger.info("Extracting channel uploads...")
    tracklist = utils.extract_tracklist(youtube, config.CHANNELS, config.NO_VIDS_EACH, config.SYNC_DAYS)

    logger.info("Finding Spotify ID's...")
    track_ids, tracklist = utils.find_track_ids(sp, tracklist, market=config.MARKET)

    logger.info("Updating playlist...")
    sp.user_playlist_replace_tracks(
        user=creds["SP_USERNAME"],
        playlist_id=creds["PLAYLIST_ID"],
        tracks=track_ids["ID"].tolist()[:config.MAX_NO],
    )

    logger.info("-----------------------------------------------------")
    logger.info("                         DONE")
    logger.info("-----------------------------------------------------")

    num_vids = tracklist.shape[0]
    num_yes = tracklist[tracklist["On Spotify"] == "Yes"].shape[0]
    num_errors = tracklist[tracklist["On Spotify"] == "Error"].shape[0]

    yes_pct = round(num_yes / num_vids * 100, 1) if num_vids else 0
    error_pct = round(num_errors / num_vids * 100, 1) if num_vids else 0

    logger.info("%s of %s tracks found on Spotify. (%s%%)", num_yes, num_vids, yes_pct)
    logger.info("%s errors. (%s%%)", num_errors, error_pct)
    logger.info("-----------------------------------------------------\n")


if __name__ == "__main__":
    main()