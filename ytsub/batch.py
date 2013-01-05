#  batch.py
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


from threading import RLock
from apiclient.errors import HttpError
from copy import deepcopy
from credentials import acquire_credentials
from apiclient.discovery import build

import random
import os
import Queue
import httplib2
import logging
import sys
import threading
import time

#TODO use priority queue.  In cmd-line application, would allow us to stream output (useful for using with pipes, if some other time-intensive task uses this as input).  Prioritize depth-first rather than bredth-first.  Perhaps just a bool option?  I dunno when you'd want bredth rather than depth first, though.
# NOTE the problem with this is if we wanted to sort the output.  BUT the unix philosophy says we shouldn't.  A tool like sort should do that. Which is convenient for streaming output!
# Don't think of the command-line tool as a USER interface -- think of what would be nice for using it as the backend for a little pyside GUI.

# How many threads to start.
NUM_THREADS = 3

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
                    min(int(self._kwargs['maxResults']), self._MAX_ITEMS - self._item_count)
    
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

def _flush_queue_to_list(queue):
    ret = []
    while not queue.empty():
        ret.append(queue.get())
        queue.task_done()
    return ret

class _Mock_Queue:
    def __init__(self):
        self.delegate = []
    def put(self, elem): 
        self.delegate.append(elem)

def batch_query(credentials, queries, thread_count=NUM_THREADS):
    request_queue = Queue.Queue()
    response_queue = _Mock_Queue() #multithreading safe because GIL
    
    
    stop = start_request_thread_pool(credentials, request_queue, response_queue, thread_count)
    
    # Put requests into task queue
    for q in queries:
        request_queue.put(q)
    
    # Wait for all the requests to finish
    request_queue.join()
    stop.set()
    
    return response_queue.delegate
    

#TODO consider converting to object using "with" statement
def start_request_thread_pool(credentials, request_queue, response_queue, thread_count):
    """Creates a thread pool to process api requests.
    Returns a threading.Event object.  When set, this stops the thread pool."""
    # TODO I don't like this event object.
    finished_event = threading.Event()
    
    def process_requests():
        http = httplib2.Http()
        http = credentials.authorize(http)
        loop = True

        while not finished_event.is_set():
            try:
                query = request_queue.get(block=True, timeout=0.01)
            except Queue.Empty:
                continue
                
            query.set_http(http)
            
            retries = 0
            while (retries < 8):
                try:
                    for response in query:
                        response_queue.put(response)
                        retries -= 1
                    
                    logging.getLogger().debug("Completed request")
                    request_queue.task_done()
                    break
                except HttpError, e:
                    retries += 1
                    logging.getLogger().info("Increasing backoff, got status code: %d" % e.resp.status)
                    time.sleep((2 ** retries) * 0.1 + (random.random() * 0.25))
                except Exception, e:
                    logging.getLogger().critical("Unexpected error in process_requests thread. Exiting. " + str(e))
                    finished_event.set()
                    
                    # HACK causes parent thread to stop if something goes wrong in this thread, at least
                    while request_queue.unfinished_tasks > 0:
                        request_queue.task_done()
                    break
            
    for i in range(thread_count):
        t = threading.Thread(target=process_requests)
        t.start()
    
    return finished_event

    
    
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
    
    for i in range(5):
        queries.append(Query(youtube.playlistItems().list, 
                {"part":"snippet", "playlistId":"UUVtt6C8Qu_ia7g2l80sY2kQ",
                "maxResults":"30",
                "fields":"items/snippet,nextPageToken"},
                MAX_ITEMS=MAX_ITEMS))
    
    
    for resp in batch_query(credentials, queries, NUM_THREADS):
        print hash(repr(resp))

def _test_chain_query(youtube, credentials):
    #TODO complete
    pass

def _test_response_stream(youtube, credentials):
    MAX_ITEMS = 75
    
    queries = [Query(youtube.playlistItems().list, {"part":"snippet",
                           "maxResults":"2",
                           "playlistId":"UUVtt6C8Qu_ia7g2l80sY2kQ",
                           "fields":"items/snippet,nextPageToken"},
                           MAX_ITEMS=MAX_ITEMS)]

    request_queue = Queue.Queue()
    response_queue = Queue.Queue()
    
    stop = start_request_thread_pool(credentials, request_queue, response_queue, NUM_THREADS)
    
    # Put requests into task queue
    for q in queries:
        request_queue.put(q)
    
    
    def process_responses():
        while not stop.is_set():
            try:
                resp = response_queue.get(block=True, timeout=0.01)
            except Queue.Empty:
                continue
            
            print hash(repr(resp))
            response_queue.task_done()
    
    response_thread = threading.Thread(target=process_responses)
    response_thread.start()
    
    # Wait for all the requests to finish
    request_queue.join()
    
    # Wait for all the responses to be handled
    response_queue.join()
    
    stop.set()

def main(argv):
    try:
        argv = FLAGS(argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, argv[0], FLAGS)
        sys.exit(1)

    logging.basicConfig()
    logging.getLogger().setLevel("ERROR")

    CLIENT_SECRETS_FILE = "../data/client_secrets.json"
    SCOPES = "https://www.googleapis.com/auth/youtube"
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    credentials = acquire_credentials(SCOPES, CLIENT_SECRETS_FILE)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))
    
    #_test_batch_query(youtube, credentials)
    #_test_batch_query_paging(youtube, credentials)
    _test_response_stream(youtube, credentials)
    





if __name__ == "__main__":
    main(sys.argv)
