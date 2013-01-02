#  main.py
#  This file is part of youtube-list 
# 
#  Copyright (C) 2013 - Jackson Williams

#  youtube-list is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  youtube-list is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with youtube-list.  If not, see <http://www.gnu.org/licenses/>.

import httplib2
import api
import logging

from apiclient.discovery import build
from credentials import acquire_credentials

def main():
    CLIENT_SECRETS_FILE = "../data/client_secrets.json"
    SCOPES = "https://www.googleapis.com/auth/youtube"
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    logging.basicConfig()
    logging.getLogger().setLevel('DEBUG')

    credentials = acquire_credentials(SCOPES, CLIENT_SECRETS_FILE)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))
        
    watched = api.get_watched_ids(youtube)
    
    new = api.get_sub_vids(youtube)
    
    unwatched_new = filter(lambda x: x.id not in watched, new)
    unwatched_new.sort(reverse=True)
    for v in unwatched_new:
        print v

if __name__ == '__main__':
    main()

