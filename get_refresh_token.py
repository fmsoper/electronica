"""
One-time helper: runs the Spotify OAuth authorization flow and prints out
a refresh token to store as the REFRESH_TOKEN secret.

Run this locally whenever you need a new refresh token - for first-time
setup, or when the current one expires (Spotify refresh tokens expire
after 6 months of inactivity).

Requires SP_CLIENT_ID, SP_CLIENT_SECRET, and REDIRECT_URI to already be
set as environment variables.
"""
import os

from spotipy.cache_handler import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth

# Must match the scope requested in main.py - a refresh token is only
# valid for the scope(s) it was issued under.
SCOPE = "playlist-modify-public"

REQUIRED_ENV_VARS = ["SP_CLIENT_ID", "SP_CLIENT_SECRET", "REDIRECT_URI"]


def main():
    missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        raise SystemExit(f"Missing required environment variable(s): {', '.join(missing)}")

    auth_manager = SpotifyOAuth(
        client_id=os.environ["SP_CLIENT_ID"],
        client_secret=os.environ["SP_CLIENT_SECRET"],
        redirect_uri=os.environ["REDIRECT_URI"],
        scope=SCOPE,
        cache_handler=MemoryCacheHandler(),
        open_browser=True,
    )

    print("Opening your browser to Spotify's consent screen...")
    print("After approving, you'll be redirected to your REDIRECT_URI.")
    print("If that shows a browser error (e.g. 'can't connect'), that's fine -")
    print("just copy the full URL from the address bar when prompted below.\n")

    auth_code = auth_manager.get_authorization_code()
    token_info = auth_manager.get_access_token(auth_code, as_dict=True, check_cache=False)

    print("\n----------------------------------------------------------------")
    print("New refresh token (copy this into your REFRESH_TOKEN secret):")
    print(token_info["refresh_token"])
    print("----------------------------------------------------------------\n")
    print("Update it at: Settings -> Secrets and variables -> Actions -> REFRESH_TOKEN")


if __name__ == "__main__":
    main()