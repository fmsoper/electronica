import os
import sys
from datetime import date

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyOauthError
from googleapiclient.discovery import build

import utils

## CREDENTIALS
YT_API_KEY = os.environ["YT_API_KEY"]
SP_CLIENT_ID = os.environ["SP_CLIENT_ID"]
SP_CLIENT_SECRET = os.environ["SP_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
REDIRECT_URI = os.environ["REDIRECT_URI"]
SP_USERNAME = os.environ["SP_USERNAME"]
PLAYLIST_ID = os.environ["PLAYLIST_ID"]


## YOUTUBE CHANNELS TO SEARCH
# GET CHANNEL ID HERE --->  https://www.streamweasels.com/tools/youtube-channel-id-and-user-id-convertor/
channels = {
    'Melodic Night': "UCDjwdJdBPQLn-hR35LXYJNw",
    'OOUKFunkyOO': "UCY2mgHbe4QiYjLHrtF5FMYQ",
    'Novaj': "UCgSC4NFr_xwN-lBfBbLqprw",
    'Maslow Unknown': "UCrgSrKO2ZUYJCirOP9bzDQg",
    'Sound Station Strategy': "UC73-NQCvIQ4FOnhgvzlS6gA",
    'hurfyd': "UCzeR0_RWnpNHe6y4DTLwE5Q",
    'Moskalus': "UC5rXILumTV11fEeq7nxWgOA",
    'rruthology': "UCw59OmZvwnXB5ivCbBNDbmw",
    'SWL 2TON': "UCZ-IRNvpmsiJmjar5V5Ksew",
    'BlueDollarBillz': "UCukVH2Rk4os9rDaU3skW63w",
    'some uncertain sir': "UCEfZoAshpTmnRjg53B13--A",
    'definite party material': "UC-IK_TuqOvv6sLSYzousUSQ",
}

no_vids_each = 20  # number of latest videos to extract from each channel, not all may be available on spotify
sync_days = 14      # number of past days to consider
max_no = 100         # maximum number of songs in the spotify playlist


## ACCESSING API'S
youtube = build('youtube', 'v3', developerKey=YT_API_KEY)

auth_manager = SpotifyOAuth(
    client_id=SP_CLIENT_ID,
    client_secret=SP_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope='playlist-modify-public',
)

try:
    token_info = auth_manager.refresh_access_token(REFRESH_TOKEN)
except SpotifyOauthError as e:
    if "invalid_grant" in str(e) or "Refresh token expired" in str(e):
        print("\n----------------------------------------------------------------")
        print("SPOTIFY REFRESH TOKEN HAS EXPIRED")
        print("As of July 2026, Spotify refresh tokens expire after 6 months.")
        print("You need to re-authorize this app and update the REFRESH_TOKEN")
        print("GitHub secret. Run get_refresh_token.py locally to generate a")
        print("new one, then update it at:")
        print("  Settings -> Secrets and variables -> Actions -> REFRESH_TOKEN")
        print("----------------------------------------------------------------\n")
        sys.exit(1)
    else:
        raise

sp = spotipy.Spotify(auth=token_info["access_token"])


# From the Youtube video titles, we extract a list of search queries
# to pass to the Spotify API
print("\nExtracting channel uploads...")
tracklist = utils.extract_tracklist(youtube, channels, no_vids_each, sync_days)

# For each query, we search Spotify and add the top song result to
# a dataframe, containing the artist(s), track name, and track ID
print("\nFinding Spotify ID's...\n")
track_ids = utils.find_track_ids(sp, tracklist)

print("\nUpdating playlist...")

sp.user_playlist_replace_tracks(
    user=SP_USERNAME,
    playlist_id=PLAYLIST_ID,
    tracks=track_ids['ID'].tolist()[:max_no],
)

print("\n-----------------------------------------------------")
print("                         DONE")
print("-----------------------------------------------------")

# Find total percentage of tracks available on Spotify
num_vids = tracklist.shape[0]
num_yes = tracklist[tracklist['On Spotify'] == "Yes"].shape[0]
num_errors = tracklist[tracklist['On Spotify'] == "Error"].shape[0]

yes_percentage = round(num_yes / num_vids * 100, 1) if num_vids else 0
error_percentage = round(num_errors / num_vids * 100, 1) if num_vids else 0

print("{} of {} tracks found on Spotify. ({}%)".format(num_yes, num_vids, yes_percentage))
print("{} errors. ({}%)".format(num_errors, error_percentage))

print("-----------------------------------------------------\n")