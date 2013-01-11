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

def get_user_playlists(youtube):
    return youtube.channels().list(
        mine=True,
        part="contentDetails"
     ).execute()['items'][0]['contentDetails']['relatedPlaylists']
    

def get_watched_ids(youtube):
    ret = []

    id_watch_history_playlist = get_user_playlists(youtube)["watchHistory"]

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
    assert MAX_VIDS >= -1
    assert MAX_AGE >= -1

    ret = []
    
    query = youtube.playlistItems().list(
            playlistId=playlist.playlist_id,
            part="snippet",
            maxResults=10)
            
    # filtering
    vidcount = 0
    cutoff_date = datetime.now() - timedelta(MAX_AGE+1) #days
    run = True        
    
    # page through results
    while run and (query is not None):
        playlist_contents_response = query.execute()
        
        for playlist_video in playlist_contents_response["items"]:
            if (vidcount != -1) and (vidcount == MAX_VIDS):
                run = False
                break
            
            video = Vid(playlist.author_name, playlist_video)
            if (MAX_AGE is not -1) and (video.date < cutoff_date):
                run = False
                break
                
            ret.append(video)
            vidcount += 1
            
        query = youtube.playlistItems().list_next(query, playlist_contents_response)
    
    return ret

def get_sub_vids(youtube, MAX_VIDS, MAX_AGE):
    ret = []
    
    channels = get_updated_channels(youtube)
    
    upload_playlists = []
    for ch in channels:
        upload_playlists.append(get_upload_playlist_of_channel(youtube, ch))
    
    for up in upload_playlists:
        ret.extend(get_videos_in_playlist(youtube, up, MAX_VIDS, MAX_AGE))
        
    return ret

def mark_watched(youtube, vids):
    history_playlist = get_user_playlists(youtube)["watchHistory"]
    
    for vid in vids:
        youtube.playlistItems().insert(part='snippet', 
                                       body={'snippet':{'playlistId':history_playlist,
                                                        'resourceId': {'videoId':vid,
                                                                       'kind':'youtube#video'}}}).execute()
    
    
    
    
    
    
    
    
