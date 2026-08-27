"""
Configuration for the YouTube -> Spotify playlist sync.

Credentials are NOT stored here - they're read from environment variables
in main.py (and, in CI, come from GitHub Actions secrets).
"""

# GET CHANNEL ID HERE --->  https://www.streamweasels.com/tools/youtube-channel-id-and-user-id-convertor/
CHANNELS = {
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

NO_VIDS_EACH = 20  # number of latest videos to check per channel
SYNC_DAYS = 14      # only consider videos uploaded in the last N days
MAX_NO = 100         # maximum number of tracks to write into the Spotify playlist
MARKET = "GB"         # Spotify market used when searching for tracks