#import warnings
#warnings.simplefilter(action='ignore', category=FutureWarning)
import os

from datetime import date

import spotipy
from spotipy.oauth2 import SpotifyOAuth
#import spotipy.util
#import spotipy.oauth2
from googleapiclient.discovery import build

import utils

## CREDENTIALS
YT_API_KEY = "REDACTED"
SP_CLIENT_ID = "8eb8231176dd446e9d7bcad802808a64"
SP_CLIENT_SECRET = "REDACTED"
REFRESH_TOKEN = "REDACTED"
REDIRECT_URI = "http://example.com"
scope = 'playlist-modify-private'


#YT_API_KEY = os.environ["YT_API_KEY"]
#SP_CLIENT_ID = os.environ["SP_CLIENT_ID"]
#SP_CLIENT_SECRET = os.environ["SP_CLIENT_SECRET"]
#ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
#REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
#REDIRECT_URI = os.environ["REDIRECT_URI"]

sp_username = "fredsphatbeets"
playlist_id = "4dhau7ZcU6QWlX6qTUjT2y"

#sp_username = os.environ["SP_USERNAME"]
#playlist_id = os.environ["PLAYLIST_ID"]
##


## YOUTUBE CHANNELS TO SEARCH
# GET CHANNEL ID HERE --->  https://www.streamweasels.com/tools/youtube-channel-id-and-user-id-convertor/
channels = {'Gazzz696': "UC2GK1jS6xrYTh4Xo9qsYSgQ",
            #'Vals': "UCR2XQYvNR0zA3FOyFYgZL8g", #old
            'OOUKFunkyOO': "UCY2mgHbe4QiYjLHrtF5FMYQ",
            'Novaj': "UCgSC4NFr_xwN-lBfBbLqprw",
            #'Stamp The Wax': "UCeGkyYcYtT3Wl2Hucv9AORg", #old
            'Maslow Unknown': "UCrgSrKO2ZUYJCirOP9bzDQg",
            #'Local Request 4991': "UCaM4FeYlEB_aEMluu6hJ2OA", #lot of house
            #'Carlos Henrique': "UCx97-AI2ONV5cIPK_Q7ogew", #Links to wrong channel
            'Sound Station Strategy': "UC73-NQCvIQ4FOnhgvzlS6gA",
            'hurfyd': "UCzeR0_RWnpNHe6y4DTLwE5Q",
            'Moskalus': "UC5rXILumTV11fEeq7nxWgOA",
            #'VSVN': "UCLySvQ5KnssdJVpbi5skvQw",
            'rruthology': "UCw59OmZvwnXB5ivCbBNDbmw",
            'SWL 2TON': "UCZ-IRNvpmsiJmjar5V5Ksew",
            'BlueDollarBillz': "UCukVH2Rk4os9rDaU3skW63w",
            'some uncertain sir': "UCEfZoAshpTmnRjg53B13--A",
            'definite party material': "UC-IK_TuqOvv6sLSYzousUSQ"}
no_vids_each = 20 #number of latest videos to extract from each channel, not all may be available on spotify

sync_days = 14 #Number of past days to consider
max_no = 100 #maximum number of songs in the spotify playlist


#old_desc = "Recent uploads from " + ", ".join(list(channels.keys())[:-1]) + ", and " + list(channels.keys())[-1] +"." + Last Updated: " + date.today().strftime("%d/%m/%Y")"
#playlist_desc =  "tracks added every monday"
##

## ACCESSING API'S
youtube = build('youtube','v3',developerKey=YT_API_KEY)

auth_manager = SpotifyOAuth(
    client_id=SP_CLIENT_ID,
    client_secret=SP_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope='playlist-modify-private',
    username=sp_username,
)
auth_manager.refresh_access_token(REFRESH_TOKEN) 
#auth_manager.token_info["access_token"] = ACCESS_TOKEN
#auth_manager.token_info["refresh_token"] = REFRESH_TOKEN
sp = spotipy.Spotify(auth_manager=auth_manager)
#SP_cred = spotipy.oauth2.SpotifyClientCredentials(SP_CLIENT_ID, SP_CLIENT_SECRET)
#token = spotipy.util.prompt_for_user_token(sp_username,
#                           'playlist-modify-private',
#                           client_id=SP_CLIENT_ID,
#                           client_secret=SP_CLIENT_SECRET,
#                           redirect_uri='http://localhost:8888/callback')
#sp = spotipy.Spotify(auth=token)
##


# From the Youtube video titles, we extract a list of search queries 
# to pass to the Spotify API
print("\nExtracting channel uploads...")
tracklist = utils.extract_tracklist(youtube, channels, no_vids_each, sync_days)

# For each query, we search Spotify and add the top song result to
# a dataframe, containing the artist(s), track name, and track ID
print("\nFinding Spotify ID's...\n")
track_ids = utils.find_track_ids(sp, tracklist)

print("\nUpdating playlist...")

sp.user_playlist_replace_tracks(user="fredsphatbeets",
                            playlist_id=playlist_id,
                            tracks=track_ids['ID'].tolist()[:max_no])

#sp.user_playlist_change_details(user="fredsphatbeets",
#                                playlist_id=playlist_id,
#                                description=playlist_desc)

print("\n-----------------------------------------------------")
print("                         DONE")
print("-----------------------------------------------------")

#Find total percentage of tracks available on Spotify
num_vids = tracklist.shape[0]
num_yes = tracklist[tracklist['On Spotify'] == "Yes"].shape[0]
num_errors = tracklist[tracklist['On Spotify'] == "Error"].shape[0]

yes_percentage = round(num_yes / num_vids * 100, 1)
error_percentage = round(num_errors / num_vids * 100, 1)

print("{} of {} tracks found on Spotify. ({}%)".format(num_yes, num_vids, yes_percentage))
print("{} errors. ({}%)".format(num_errors, error_percentage))

#Find the percentage of respective channel uploads that are available on Spotify
#print("\n"+analysis.percent_on_spotify(tracklist).to_string(index=False))

print("-----------------------------------------------------\n")
