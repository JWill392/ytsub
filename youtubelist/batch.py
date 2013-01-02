#  batch.py
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


from threading import RLock
from apiclient.errors import HttpError
from copy import deepcopy
from credentials import acquire_credentials
from apiclient.discovery import build

import random
import os
import Queue
import gflags
import httplib2
import logging
import sys
import threading
import time

# How many threads to start.
NUM_THREADS = 3

# Length of Goog API's page tokens
PAGE_TOKEN_LENGTH = 6

FLAGS = gflags.FLAGS
gflags.DEFINE_enum('logging_level', 'ERROR',
        ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        'Set the level of logging detail.')

class Query:
    def __init__(self, request_function, kwargs, http=None, MAX_ITEMS=-1):
        self._request_function = request_function
        self._item_count = 0
        self._MAX_ITEMS = MAX_ITEMS
        self._http = http
        self._done = ""
        
        if 'maxResults' not in kwargs:
            kwargs['maxResults'] = 50
        self._kwargs = kwargs
    
    def set_http(self, http):
        self._http = http
    
    def get_total_items(self):
        return self._item_count
    
    def __iter__(self):
        return self
    
    def next(self):
        if self._done:
            raise StopIteration(self._done)
    
        if self._http is None:
            raise ValueError("http is None")
    
        # prevent last fetch overshoot
        if self._MAX_ITEMS is not -1:
            self._kwargs['maxResults'] = \
                    min(self._kwargs['maxResults'], self._MAX_ITEMS - self._item_count)
    
        # send REST API request and wait for response
        response = self._request_function(**self._kwargs).execute(http=self._http)
        try:
            self._item_count += len(response['items'])
        except KeyError:
            pass # no items

        
        # done? client-imposed item max reached
        if self._MAX_ITEMS is not -1 and self.get_total_items() == self._MAX_ITEMS:
            self._done = "received MAX_ITEMS items (%i)" % self._item_count
            return response
            
        # done? server exhausted (no more items avail)
        if 'nextPageToken' not in response:
            self._done = "Server has no more items"
            return response
        
        # not done; page query kwargs
        self._kwargs["pageToken"] = response["nextPageToken"]
        return response


def batch_query(credentials, queries, thread_count):
    """Create the thread pool to process the requests."""
    responses = []
    responses_lock = RLock()
    
    query_queue = Queue.Queue()
    
    def process_requests(n):
        http = httplib2.Http()
        http = credentials.authorize(http)
        loop = True

        while loop:
            query = query_queue.get()
            query.set_http(http)
            for n in range(0, 7):
                try:
                    for response in query:
                        with responses_lock:
                            responses.append(response)
                    
                    logging.getLogger().debug("Completed request")
                    query_queue.task_done()
                    break
                except HttpError, e:
                    logging.getLogger().info("Increasing backoff, got status code: %d" % e.resp.status)
                    time.sleep((2 ** n) * 0.1 + (random.random() * 0.25))

    for i in range(thread_count):
        t = threading.Thread(target=process_requests, args=[i])
        t.daemon = True
        t.start()
        
    # Put requests into task queue
    for q in queries:
        query_queue.put(q)
    
    # Wait for all the requests to finish
    query_queue.join()
    return responses
    
    
def _test_batch_query(youtube, credentials):
    queries = []
    for i in range(20):
    #request_function, kwargs, http=None, MAX_ITEMS=-1
        queries.append(Query(youtube.channels().list, 
                {"mine":True, "part":"contentDetails"}))
    
    
    for resp in batch_query(credentials, queries, NUM_THREADS):
        print resp

def _test_batch_query_paging(youtube, credentials):
    MAX_ITEMS = 75
    queries = []
    
    for i in range(20):
        queries.append(Query(youtube.playlistItems().list, 
                {"part":"snippet", "playlistId":"UUVtt6C8Qu_ia7g2l80sY2kQ",
                "fields":"items/snippet,nextPageToken"},
                MAX_ITEMS=MAX_ITEMS))
    
    
    for resp in batch_query(credentials, queries, NUM_THREADS):
        print hash(repr(resp))


def main(argv):
    try:
        argv = FLAGS(argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, argv[0], FLAGS)
        sys.exit(1)

    logging.basicConfig()
    logging.getLogger().setLevel(getattr(logging, FLAGS.logging_level))

    CLIENT_SECRETS_FILE = "../data/client_secrets.json"
    SCOPES = "https://www.googleapis.com/auth/youtube"
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    credentials = acquire_credentials(SCOPES, CLIENT_SECRETS_FILE)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))
    
    #_test_batch_query(youtube, credentials)
    _test_batch_query_paging(youtube, credentials)
    





if __name__ == "__main__":
    main(sys.argv)
