import pandas as pd
from datetime import date, timedelta

def extract_details(video):
    """ 
    Extract artists, track name, and publish date from video
    """

    whitelist = [" feat."," ft.", " feat",
                " edit", " mix", " remix",
                " tweak", " flip", " dub", " re-edit"]
    blacklist = ["extended", "original", "radio", "promo", "premiere"]


    video_title = video['snippet']['title'].lower()
    

    # case for when || in title, as for "bluedollarbillz" channel
    if " || " in video_title:
        video_title = video_title.split(" || ", 1)[0]

    # case for when || in title, as for "some uncertain sir" channel
    if " | " in video_title:
        video_title = video_title.split(" | ", 1)[0]
    for word in blacklist:
        video_title = video_title.replace("["+word+"]","")

    if " - " not in video_title:
        artists, track_name, video_date = "","",""
    elif "(" and ")" in video_title and " - " in video_title.split("(", 1)[1].split(")")[0]:
        artists, track_name, video_date = "","",""
    elif "[" and "]" in video_title and " - " in video_title.split("[", 1)[1].split("]")[0]:
        artists, track_name, video_date = "","",""
    else:
        video_title = video_title.split(" - ", 1)


        video_date = video['snippet']['publishedAt']
        for ele in ["-", "T", ":", "Z"]:
            video_date = video_date.replace(ele,"")


        artists = video_title[0]
        for ele in [" feat. ", " ft. ", " feat ", " ft ",
                    " , ", ", ", " x ", " X ", " vs. ", " vs "]:
            artists = artists.replace(ele," & ")
        artists = artists.split(" & ")


        track_name = video_title[1]
        while "(" and ")" in track_name:
            round_brackets = track_name.split("(", 1)[1].split(")")[0]
            track_name = track_name.replace("("+round_brackets+")","")
            
            if any(word in round_brackets for word in whitelist):
                if round_brackets.split(" ")[0] in blacklist:
                    round_brackets = ""
                else:
                    for word in whitelist:
                        round_brackets = round_brackets.replace(word,"")
            else:
                round_brackets = ""
            
            extra_artists = round_brackets.split(" & ")
            artists.extend(extra_artists)

        while "[" and "]" in track_name:
            square_brackets = track_name.split("[", 1)[1].split("]")[0]
            track_name = track_name.replace("["+square_brackets+"]","")
            
            if any(word in square_brackets for word in whitelist):
                if square_brackets.split(" ")[0] in blacklist:
                    square_brackets = ""
                else:
                    for word in whitelist:
                        square_brackets = square_brackets.replace(word,"")
            else:
                square_brackets = ""
            
            extra_artists = square_brackets.split(" & ")
            artists.extend(extra_artists)
        
        for ele in [" feat. ", " ft. ", " feat ", " ft "]:
            track_name.replace(ele," ")


        artists = [x.strip() for x in artists if x.strip()]
        artists = " ".join(str(e) for e in artists)

        return [artists, track_name, video_date]






def extract_tracklist(youtube, channels, num_vids_each, sync_days):
    """
    Produce a dataframe containing the artists and track names for the latest uploaded videos
    """

    tracklist = []

    for username, channelId in channels.items():
        contentdata = youtube.channels().list(id=channelId,part='contentDetails').execute()
        playlist_id = contentdata['items'][0]['contentDetails']['relatedPlaylists']['uploads']


        res = youtube.playlistItems().list(playlistId=playlist_id,
                                            part='snippet',
                                            maxResults=num_vids_each).execute()

        for video in res['items']:
            try:
                video_details = extract_details(video)
                if video_details != None:
                    track = {
                        'Artist(s)':video_details[0],
                        'Title':video_details[1],
                        'Upload Time':video_details[2],
                        'Channel':username
                    }
                    tracklist.append(track)
            except: pass

        tracklist = pd.DataFrame(tracklist)
        print(username + " : DONE")

    pd.set_option("display.max_rows", 1000)

    expiry_date = (date.today() - timedelta(days=sync_days)).strftime("%Y%m%d%H%M%S")
    tracklist = tracklist[ tracklist['Upload Time'] >= expiry_date ]

    return tracklist.sort_values('Upload Time', ascending=False, ignore_index=True)





def find_track_ids(spotify, tracklist):
    track_ids = []
    tracklist["On Spotify"] = ""

    for index, row in tracklist.iterrows():
        query = "track:" +str(row['Title']) + " " + "artist:" + str(row['Artist(s)'])

        search_output = spotify.search(q=query, type="track", limit=1, market='GB')
        if search_output["tracks"]["total"] == 0:
            tracklist.at[index, "On Spotify"] = 'No'
            continue
        else:
            tracklist.at[index, "On Spotify"] = 'Yes'
            id = search_output["tracks"]["items"][0]["id"]
            
            try:
                track = spotify.track("spotify:track:"+id)
            except:
                tracklist.at[index, "On Spotify"] = 'Error'
                continue

            artists = []
            for i in range(0, len(track["artists"])):
                artists.append(track["artists"][i]["name"])
            artists = ", ".join(artists)

            track_ids.append(
                {
                    'Artist(s)':artists,
                    'Track':track["name"],
                    'ID':id
                }
            )
    
    track_ids = pd.DataFrame(track_ids)

    complete_tracklist = tracklist.sort_values('Upload Time', ascending=False, ignore_index=True)
    #complete_tracklist.to_csv('tracklist.csv', index=False)
    print(complete_tracklist.shift()[1:])

    return track_ids



