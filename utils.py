import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Tags that mark a bracketed group as a remix/edit credit worth keeping
# (and pulling extra artist names out of), e.g. "(Some DJ Remix)".
WHITELIST_TAGS = [
    " feat.", " ft.", " feat", " ft",
    " edit", " mix", " remix",
    " tweak", " flip", " dub", " re-edit",
]
# If a bracketed group starts with one of these words, it's a plain
# version tag (e.g. "(Extended Mix)") rather than a remix credit, and
# gets discarded instead of mined for artist names.
BLACKLIST_TAGS = ["extended", "original", "radio", "promo", "premiere"]

# Separators between multiple artists in the "Artist - Title" part of a
# title, normalised down to " & " before splitting into a list.
ARTIST_SEPARATORS = [
    " feat. ", " ft. ", " feat ", " ft ",
    " , ", ", ", " x ", " X ", " vs. ", " vs ",
]
# Leftover feat/ft fragments to strip from the track name once any bracketed
# remix credits have already been pulled out of it.
FEAT_FRAGMENTS = [" feat. ", " ft. ", " feat ", " ft "]


def _extract_bracket_content(text: str, open_char: str, close_char: str) -> tuple[str, list[str]]:
    """
    Repeatedly strip bracketed groups (e.g. "(...)" or "[...]") out of `text`.

    A group is treated as a remix/edit credit - and mined for extra artist
    names - if it contains one of WHITELIST_TAGS and doesn't start with a
    BLACKLIST_TAGS word (e.g. "(Some DJ Remix)" keeps "Some DJ" as an extra
    artist, "(Extended Mix)" is just discarded). Anything else in brackets
    is discarded outright (feature credits, random annotations, etc).

    Returns (text_with_brackets_removed, list_of_extra_artist_names).
    """
    extra_artists: list[str] = []

    while open_char in text and close_char in text:
        inner = text.split(open_char, 1)[1].split(close_char, 1)[0]
        text = text.replace(f"{open_char}{inner}{close_char}", "")

        is_remix_tag = any(tag in inner for tag in WHITELIST_TAGS)
        starts_with_blacklisted = inner.split(" ")[0] in BLACKLIST_TAGS

        if is_remix_tag and not starts_with_blacklisted:
            for tag in WHITELIST_TAGS:
                inner = inner.replace(tag, "")
            extra_artists.extend(inner.split(" & "))

    return text, extra_artists


def extract_details(video: dict) -> Optional[dict]:
    """
    Extract artist(s), track name, and upload time from a YouTube video's
    snippet, assuming an "Artist - Title" style upload title.

    Returns None if the title doesn't look like that format at all (no
    " - "), or if the only " - " present is inside a bracketed tag rather
    than separating an artist from a title.
    """
    title = video["snippet"]["title"].lower()

    # Some channels append extra context after " | " or " || " - drop it.
    for separator in (" || ", " | "):
        if separator in title:
            title = title.split(separator, 1)[0]

    for tag in BLACKLIST_TAGS:
        title = title.replace(f"[{tag}]", "")

    has_round_brackets = "(" in title and ")" in title
    has_square_brackets = "[" in title and "]" in title

    dash_in_round_brackets = has_round_brackets and " - " in title.split("(", 1)[1].split(")", 1)[0]
    dash_in_square_brackets = has_square_brackets and " - " in title.split("[", 1)[1].split("]", 1)[0]

    if " - " not in title or dash_in_round_brackets or dash_in_square_brackets:
        return None

    artist_part, track_part = title.split(" - ", 1)

    upload_time = datetime.strptime(video["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")

    artists = artist_part
    for separator in ARTIST_SEPARATORS:
        artists = artists.replace(separator, " & ")
    artists = [a.strip() for a in artists.split(" & ") if a.strip()]

    track_name, round_extra_artists = _extract_bracket_content(track_part, "(", ")")
    track_name, square_extra_artists = _extract_bracket_content(track_name, "[", "]")
    artists.extend(round_extra_artists)
    artists.extend(square_extra_artists)

    for fragment in FEAT_FRAGMENTS:
        track_name = track_name.replace(fragment, " ")
    track_name = " ".join(track_name.split())  # collapse any leftover double spaces

    return {
        "Artist(s)": " & ".join(a.strip() for a in artists if a.strip()),
        "Title": track_name,
        "Upload Time": upload_time,
    }


def extract_tracklist(youtube, channels: dict, num_vids_each: int, sync_days: int) -> pd.DataFrame:
    """
    Produce a dataframe of artist/track/upload-time/channel for each
    channel's videos uploaded within the last `sync_days` days.
    """
    tracklist = []

    for channel_name, channel_id in channels.items():
        channel_data = youtube.channels().list(id=channel_id, part="contentDetails").execute()
        uploads_playlist_id = channel_data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        playlist_items = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="snippet",
            maxResults=num_vids_each,
        ).execute()

        for video in playlist_items["items"]:
            try:
                details = extract_details(video)
            except (KeyError, IndexError) as e:
                logger.warning("Skipping an unparseable video on %s: %s", channel_name, e)
                continue

            if details is not None:
                details["Channel"] = channel_name
                tracklist.append(details)

        logger.info("%s: done", channel_name)

    columns = ["Artist(s)", "Title", "Upload Time", "Channel"]
    tracklist_df = pd.DataFrame(tracklist, columns=columns)

    if tracklist_df.empty:
        return tracklist_df

    pd.set_option("display.max_rows", 1000)
    cutoff = datetime.now() - timedelta(days=sync_days)
    tracklist_df = tracklist_df[tracklist_df["Upload Time"] >= cutoff]

    return tracklist_df.sort_values("Upload Time", ascending=False, ignore_index=True)


def find_track_ids(spotify, tracklist: pd.DataFrame, market: str = "GB") -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    For each row in `tracklist`, search Spotify for a matching track.

    Returns (track_ids, annotated_tracklist):
      - track_ids: dataframe of just the tracks that were found, with their Spotify IDs.
      - annotated_tracklist: a *copy* of `tracklist` (the caller's dataframe is left
        untouched) with an added "On Spotify" column ("Yes" / "No" / "Error").
    """
    track_ids = []
    tracklist = tracklist.copy()
    tracklist["On Spotify"] = ""

    for index, row in tracklist.iterrows():
        query = f"track:{row['Title']} artist:{row['Artist(s)']}"

        try:
            results = spotify.search(q=query, type="track", limit=1, market=market)
        except Exception as e:
            logger.warning("Spotify search failed for %r: %s", query, e)
            tracklist.at[index, "On Spotify"] = "Error"
            continue

        matches = results["tracks"]["items"]
        if not matches:
            tracklist.at[index, "On Spotify"] = "No"
            continue

        tracklist.at[index, "On Spotify"] = "Yes"
        track = matches[0]
        artists = ", ".join(artist["name"] for artist in track["artists"])

        track_ids.append({
            "Artist(s)": artists,
            "Track": track["name"],
            "ID": track["id"],
        })

    track_ids_df = pd.DataFrame(track_ids, columns=["Artist(s)", "Track", "ID"])

    complete_tracklist = tracklist.sort_values("Upload Time", ascending=False, ignore_index=True)
    logger.info("\n%s", complete_tracklist)

    return track_ids_df, complete_tracklist