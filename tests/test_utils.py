from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pandas as pd
import pytest

import utils


@pytest.fixture
def make_video():
    """Factory fixture: builds a fake YouTube API video dict for a given title."""
    def _make(title, published="2026-01-01T12:00:00Z"):
        return {"snippet": {"title": title, "publishedAt": published}}
    return _make


@pytest.mark.parametrize(
    "title, expected_artists, expected_title",
    [
        ("Artist Name - Track Name", "artist name", "track name"),
        ("Artist One feat. Artist Two - Track", "artist one & artist two", "track"),
        ("Artist - Track Name (Extended Mix)", "artist", "track name"),
    ],
    ids=["basic-artist-title", "feat-splits-into-multiple-artists", "version-tag-discarded-not-credited"],
)
def test_extract_details_parsing(make_video, title, expected_artists, expected_title):
    result = utils.extract_details(make_video(title))
    assert result["Artist(s)"] == expected_artists
    assert result["Title"] == expected_title


def test_basic_upload_time_is_parsed_as_datetime(make_video):
    result = utils.extract_details(make_video("Artist Name - Track Name", published="2026-01-01T12:00:00Z"))
    assert result["Upload Time"] == datetime(2026, 1, 1, 12, 0, 0)


def test_no_dash_returns_none(make_video):
    assert utils.extract_details(make_video("Just A Title No Dash")) is None


def test_dash_only_inside_round_brackets_returns_none(make_video):
    # the only " - " is inside the brackets, not separating artist/title
    assert utils.extract_details(make_video("Some Video (Live - 2024)")) is None


def test_lone_closing_paren_does_not_crash(make_video):
    # Regression test for the original "(" and ")" in title bug: due to
    # Python operator precedence that condition only ever checked for ")",
    # so a title with a stray ")" but no "(" would raise IndexError when
    # the code tried to split on a "(" that wasn't there.
    result = utils.extract_details(make_video("Artist :) - Track Name"))
    assert result is not None
    assert result["Title"] == "track name"


def test_remix_credit_in_brackets_adds_extra_artist(make_video):
    result = utils.extract_details(make_video("Artist - Track Name (Someone Remix)"))
    assert result["Title"] == "track name"
    assert "someone" in result["Artist(s)"]
    assert "artist" in result["Artist(s)"]


def test_feat_fragment_after_brackets_is_stripped(make_video):
    # Regression test for the original track_name.replace(...) bug, where
    # the result was discarded (strings are immutable) so " feat." was
    # silently left sitting in the track name.
    result = utils.extract_details(make_video("Artist - Track Name feat. Someone (Remix)"))
    assert "feat" not in result["Title"]


def test_extract_tracklist_filters_by_sync_days(make_video):
    old_video = make_video(
        "Old Artist - Old Track",
        published=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    new_video = make_video(
        "New Artist - New Track",
        published=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    youtube = MagicMock()
    youtube.channels().list().execute.return_value = {
        "items": [{"contentDetails": {"relatedPlaylists": {"uploads": "PL123"}}}]
    }
    youtube.playlistItems().list().execute.return_value = {"items": [old_video, new_video]}

    result = utils.extract_tracklist(youtube, {"TestChannel": "UC123"}, num_vids_each=5, sync_days=14)

    assert len(result) == 1
    assert result.iloc[0]["Title"] == "new track"


def test_extract_tracklist_handles_no_matching_videos(make_video):
    youtube = MagicMock()
    youtube.channels().list().execute.return_value = {
        "items": [{"contentDetails": {"relatedPlaylists": {"uploads": "PL123"}}}]
    }
    youtube.playlistItems().list().execute.return_value = {"items": [make_video("No Dash Title Here")]}

    result = utils.extract_tracklist(youtube, {"TestChannel": "UC123"}, num_vids_each=5, sync_days=14)
    assert result.empty


def test_find_track_ids_marks_found_and_not_found():
    now = datetime.now()
    tracklist = pd.DataFrame([
        {"Artist(s)": "artist a", "Title": "track a", "Upload Time": now, "Channel": "c"},
        {"Artist(s)": "artist b", "Title": "track b", "Upload Time": now - timedelta(hours=1), "Channel": "c"},
    ])

    spotify = MagicMock()
    spotify.search.side_effect = [
        {"tracks": {"items": [{"id": "id1", "name": "Track A", "artists": [{"name": "Artist A"}]}]}},
        {"tracks": {"items": []}},
    ]

    track_ids, annotated = utils.find_track_ids(spotify, tracklist)

    assert len(track_ids) == 1
    assert track_ids.iloc[0]["ID"] == "id1"
    assert list(annotated["On Spotify"]) == ["Yes", "No"]
    # the caller's original dataframe must be untouched (no hidden mutation)
    assert "On Spotify" not in tracklist.columns


def test_find_track_ids_marks_search_exception_as_error():
    tracklist = pd.DataFrame([
        {"Artist(s)": "artist a", "Title": "track a", "Upload Time": datetime.now(), "Channel": "c"},
    ])

    spotify = MagicMock()
    spotify.search.side_effect = Exception("boom")

    track_ids, annotated = utils.find_track_ids(spotify, tracklist)

    assert len(track_ids) == 0
    assert list(annotated["On Spotify"]) == ["Error"]