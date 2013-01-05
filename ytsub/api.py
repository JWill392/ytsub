#  api.py
#  This file is part of ytsub 
# 
#  Copyright (C) 2013 - Jackson Williams

#  ytsub is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  ytsub is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with ytsub.  If not, see <http://www.gnu.org/licenses/>.

from video import Vid
from datetime import datetime
from datetime import timedelta

class _Channel:
    def __init__(self, channel_response):
        self.title = channel_response["snippet"]["title"]
        self.channel_id = channel_response["snippet"]["resourceId"]["channelId"]

class _UploadPlaylist:
    def __init__(self, for_channel, channel_list_response):
        self.author_name = for_channel.title
        self.playlist_id = \
                channel_list_response["items"][0]["contentDetails"]\
                ["relatedPlaylists"]["uploads"]

def get_watched_ids(youtube):
    ret = []

    playlists_response = youtube.channels().list(
        mine=True,
        part="contentDetails"
     ).execute()

    id_watch_history_playlist = playlists_response["items"][0]["contentDetails"]["relatedPlaylists"]["watchHistory"]

    query = youtube.playlistItems().list(
        playlistId=id_watch_history_playlist,
        part="id",
        maxResults=50,
        fields="items(id,kind),nextPageToken")
        
    while query is not None:
        recently_watched_response = query.execute()

        for vid in recently_watched_response["items"]:
            ret.append(vid["id"])
        
        query = youtube.playlistItems().list_next(query, recently_watched_response)
        
    return ret

def get_updated_channels(youtube):
    updated_channels = []
    
    next_page_token = ""
    while next_page_token is not None:
        sub_channels_response = youtube.subscriptions().list(
            mine=True,
            part="snippet",
            maxResults=50,
            order="unread",
            fields="items/snippet,nextPageToken"
        ).execute()
        
        for channel in sub_channels_response["items"]:
            updated_channels.append(_Channel(channel))
        
        next_page_token = sub_channels_response.get("nextPageToken")

    return updated_channels

def get_upload_playlist_of_channel(youtube, channel):
    channel_list_response = id_uploads = youtube.channels().list(
        id=channel.channel_id,
        part="contentDetails",
        fields="items/contentDetails",
        maxResults=1
        ).execute()
    return _UploadPlaylist(channel, channel_list_response)

def get_videos_in_playlist(youtube, playlist, MAX_VIDS, MAX_AGE):
    ret = []
    
    vidcount = 0
    query = youtube.playlistItems().list(
            playlistId=playlist.playlist_id,
            part="snippet",
            maxResults=50)
    while (query is not None) and (vidcount < MAX_VIDS):
        playlist_contents_response = query.execute()
        
        cutoff_date = datetime.now() - timedelta(MAX_AGE) #days
        for playlist_video in playlist_contents_response["items"]:
            video = Vid(playlist.author_name, playlist_video)
            if (video.date < cutoff_date):
                break
            ret.append(video)
        vidcount += len(playlist_contents_response["items"])
        query = youtube.playlistItems().list_next(query, playlist_contents_response)
    
    return ret

def get_sub_vids(youtube):
    ret = []
    
    channels = get_updated_channels(youtube)
    
    upload_playlists = []
    for ch in channels:
        upload_playlists.append(get_upload_playlist_of_channel(youtube, ch))
    
    for up in upload_playlists:
        ret.extend(get_videos_in_playlist(youtube, up, 20, 10))
        
    return ret
