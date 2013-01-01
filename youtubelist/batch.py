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
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with youtube-list.    If not, see <http://www.gnu.org/licenses/>.


from threading import RLock
from apiclient.errors import HttpError
from copy import deepcopy
from credentials import acquire_credentials
from apiclient.discovery import build

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
    def __init__(self, request_function, kwargs, on_response):
        self._request_function = request_function
        self._kwargs = kwargs
        self._on_response = on_response
    
    def page(self, response):
        self._kwargs["pageToken"] = response["nextPageToken"]
     
    def execute(self, task_queue, http):
        response = self._request_function(**self._kwargs).execute(http)
        self._on_response(task_queue, response)



class _Backoff:
    """Exponential Backoff

    Implements an exponential backoff algorithm.
    Instantiate and call loop() each time through
    the loop, and each time a request fails call
    fail() which will delay an appropriate amount
    of time.
    """

    def __init__(self, maxretries=8):
        self.retry = 0
        self.maxretries = maxretries
        self.first = True

    def loop(self):
        if self.first:
            self.first = False
            return True
        else:
            return self.retry < self.maxretries

    def fail(self):
        self.retry += 1
        delay = 2 ** self.retry
        time.sleep(delay)
        
def batch_query(credentials, requests):
    req_queue = Queue.Queue()

    start_request_threads(req_queue, credentials, NUM_THREADS)

    # Put requests into task queue
    for req in requests:
        req_queue.put(req)
        
    
    # Wait for all the requests to finish
    req_queue.join()

def start_request_threads(request_queue, credentials, thread_count):
    """Create the thread pool to process the requests.
    Put None onto queue to terminate thread"""
    
    def process_requests(n):
        http = httplib2.Http()
        http = credentials.authorize(http)
        loop = True

        while loop:
            query = request_queue.get()
            backoff = _Backoff()
            while backoff.loop():
                try:
                    query.execute(request_queue, http)
                    break
                except HttpError, e:
                    if e.resp.status in [402, 403, 408, 500, 503, 504]:
                        logging.getLogger().info("Increasing backoff, got status code: %d" % e.resp.status)
                        backoff.fail()
                #except Exception, e:
                #    logging.getLogger().critical("Unexpected error. Exiting." + str(e))
                #    loop = False
                #    break

            logging.getLogger().debug("Completed request")
            request_queue.task_done()

    for i in range(thread_count):
        t = threading.Thread(target=process_requests, args=[i])
        t.daemon = True
        t.start()


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
    
    watched_lock = RLock()
    watched_id_responses = []
    def on_watched_response(task_queue, response):
        with watched_lock:
            watched_id_responses.append(response)
        
    
    queries = []
    for i in range(20):
        queries.append(Query(youtube.channels().list, {
                "mine":True, "part":"contentDetails"
                }, on_watched_response))
    
    batch_query(credentials, queries)
    for resp in watched_id_responses:
        print resp



if __name__ == "__main__":
    main(sys.argv)
