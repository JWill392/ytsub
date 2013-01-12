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

import ytsub.batch as batch

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

def get_user_playlists(youtube, credentials):
    return youtube.channels().list(
        mine=True,
        part="contentDetails"
     ).execute()['items'][0]['contentDetails']['relatedPlaylists']
    

def get_watched_ids(youtube, credentials):
    ret = []

    id_watch_history_playlist = get_user_playlists(youtube, credentials)["watchHistory"]

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

def get_updated_channels(youtube, credentials):
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

def channel_playlists_query(youtube, credentials, channel):
    return batch.Query(youtube.channels().list, 
                 {'id':channel.channel_id,
                  'part':'contentDetails',
                  'fields':'items/contentDetails'},
                  limit=batch.QueryLimitCount(1))

def get_videos_in_playlists(youtube, credentials, playlist_list, MAX_VIDS, MAX_AGE):
    assert MAX_VIDS >= -1
    assert MAX_AGE >= -1

    playlist_queries = []
    
    for playlist in playlist_list:
        query = batch.Query(youtube.playlistItems().list,
                            {'playlistId':playlist.playlist_id,
                             'part':'snippet'},
                            limit=(batch.QueryLimitCount(MAX_VIDS),
                                   batch.QueryLimitAge(MAX_AGE)))
        query._name = playlist
        playlist_queries.append(query)
    
    resps = batch.batch_query(batch.get_http_factory(credentials), playlist_queries)
    uploaded_vids = []
    for r in resps:
        author = r[0]._name.author_name
        response = r[2]
        
        uploaded_vids.extend([Vid(author, item) for item in response['items']])
    
    return uploaded_vids

def get_sub_vids(youtube, credentials, MAX_VIDS, MAX_AGE):
    channels = get_updated_channels(youtube, credentials)
    
    playlist_queries = []
    for ch in channels:
        q = channel_playlists_query(youtube, credentials, ch)
        q._name = ch
        playlist_queries.append(q)
    
    resps = batch.batch_query(batch.get_http_factory(credentials), playlist_queries)
    upload_playlists = [_UploadPlaylist(r[0]._name, r[2]) for r in resps]
    
    return get_videos_in_playlists(youtube, credentials, upload_playlists, MAX_VIDS, MAX_AGE)

def mark_watched(youtube, credentials, vids):
    history_playlist = get_user_playlists(youtube, credentials)["watchHistory"]
    
    for vid in vids:
        youtube.playlistItems().insert(part='snippet', 
                                       body={'snippet':{'playlistId':history_playlist,
                                                        'resourceId': {'videoId':vid,
                                                                       'kind':'youtube#video'}}}).execute()
    
    
    
