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

import argparse
import sys
import httplib2
import api
import logging
import fileinput
import re

from __init__ import __version__
from apiclient.discovery import build
from credentials import acquire_credentials
from argparse_util import ListOrStdinAction

__vid_regex = re.compile(r'^(?:(?:(?:(?:http://)?www\.)?youtube\.com/watch\?\S*?v='
                       r')?([a-zA-Z0-9_-]{11})\S*)$')
def videoID(url_or_id):
    match = __vid_regex.match(url_or_id)
    if not match:
        raise ValueError('Value must be a youtube video id or the watch url')
    return match.group(1)
    

def _setup():
    CLIENT_SECRETS_FILE = "../data/client_secrets.json"
    SCOPES = "https://www.googleapis.com/auth/youtube"
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    logging.basicConfig()

    credentials = acquire_credentials(SCOPES, CLIENT_SECRETS_FILE)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))
        
    return (youtube, credentials)



def main():
    parser = argparse.ArgumentParser(
                    description='List your new Youtube subscription videos.',
                    epilog='Report %(prog)s bugs to '
                           '<https://github.com/JWill392/youtube-list/issues>'
             )
    parser.add_argument('--mark-watched', type=videoID,
                        action=ListOrStdinAction, metavar='Video ID')
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('--version', action='version', 
                        version='%(prog)s '+__version__)
    
    args = parser.parse_args()
    
    # handle verbose
    logging.getLogger().setLevel(('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG')[args.verbose])
    
    
    
    print args
    
    youtube, credentials = _setup()
        
    #watched = api.get_watched_ids(youtube)
    #new = api.get_sub_vids(youtube)
    #unwatched_new = filter(lambda x: x.id not in watched, new)
    #unwatched_new.sort(reverse=True)
    #for v in unwatched_new:
    #    print v

if __name__ == '__main__':
    main()

