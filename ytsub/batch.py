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
from pprint import pprint

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

# How many threads to use
NUM_THREADS = 3

class Query:
    def __init__(self, request_function, kwargs, http=None, MAX_ITEMS=-1):
        self._request_function = request_function
        self._item_count = 0
        self._MAX_ITEMS = MAX_ITEMS
        self._http = http
        self._done = ""
        
        # adjusted down later if MAX_ITEMS less than 50
        if 'maxResults' not in kwargs:
            kwargs['maxResults'] = 50
        self._kwargs = kwargs
    
    def set_http(self, http):
        self._http = http
    
    def get_total_items(self):
        return self._item_count
    
    def __iter__(self):
        return self
    
    #TODO raise error if haven't yet called next
    def get_last_request(self):
        return {'function':self._request_function,
                'kwargs':deepcopy(self._kwargs)}
    
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

        
        # done if client-imposed item max reached
        if self._MAX_ITEMS is not -1 and self.get_total_items() == self._MAX_ITEMS:
            self._done = "received MAX_ITEMS items (%i)" % self._item_count
            return response
            
        # done if server exhausted (no more items avail)
        if 'nextPageToken' not in response:
            self._done = "Server has no more items"
            return response
        
        # not done; page query kwargs
        self._kwargs["pageToken"] = response["nextPageToken"]
        return response

def _clear_queue_tasks(queue):
    while queue.unfinished_tasks > 0:
        queue.task_done()

class RequestThreadPool:
    """Creates a thread pool to process api requests.
    Used with with statement."""
    def __init__(self, authorized_http_factory, on_response_func, thread_count=NUM_THREADS):
        self._authorized_http_factory = authorized_http_factory
        self._THREAD_COUNT = thread_count
        self._on_response_func = on_response_func

        self._request_queue = Queue.Queue()
        self._response_queue = Queue.Queue()
        self._exit_event = None
    
    def put_request(self, request):
        self._request_queue.put(request)
    
    # TODO way for client to decide to __exit__ in on_response_func
    def join(self):
        self._request_queue.join()
        self._response_queue.join()
    
    def _process_responses(self):
        while not self._exit_event.is_set() or \
              not self._response_queue.empty():
            try:
                response = self._response_queue.get(block=True, timeout=0.01)
            except Queue.Empty:
                continue
            
            self._on_response_func(*response)
            self._response_queue.task_done()
        logging.getLogger().debug('Exiting _process_responses thread')  
        
    def _process_requests(self):
        http = self._authorized_http_factory()
        loop = True

        while not self._exit_event.is_set():
            try:
                query = self._request_queue.get(block=True, timeout=0.01)
            except Queue.Empty:
                continue
                
            query.set_http(http)
            
            http_failures = 0
            while True: # retry executing query
                try:
                    for response in query: # execute each page of query
                        self._response_queue.put((query, query.get_last_request(), response))
                        http_failures -= 1
                    self._request_queue.task_done()
                    break
                except HttpError, e:
                    if http_failures > 8: # TODO write testcase for this -- have never executed this code
                        logging.getLogger().critical("Http requests failed too many times.  Exiting. " + str(e))
                        self.__exit__(*sys.exc_info())
                        break
                    http_failures += 1
                    logging.getLogger().info("Increasing backoff, got status code: %d" % e.resp.status)
                    time.sleep((2 ** http_failures) * 0.1 + (random.random() * 0.25))
                except Exception, e:
                    logging.getLogger().critical("Unexpected error in process_requests thread. Exiting. " + str(e))
                    self.__exit__(*sys.exc_info())
                    break
        logging.getLogger().debug('Exiting _process_requests thread')  
                    
    
    
    def __enter__(self):
        self._exit_event = threading.Event()
        for i in range(self._THREAD_COUNT):
            t = threading.Thread(target=self._process_requests)
            t.start()
        
        resp_thread = threading.Thread(target=self._process_responses)
        resp_thread.start()
        
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        logging.getLogger().debug('Exiting RequestThreadPool context.')
        self._exit_event.set()
        _clear_queue_tasks(self._request_queue)
        _clear_queue_tasks(self._response_queue)
        return False #Don't supress exceptions

def authorized_http_factory(credentials):
    return lambda : credentials.authorize(httplib2.Http())

def batch_query(http_factory, queries):
    '''Simple interface to RequestThreadPool to return a simple list of 
    responses to queries'''
    ret = []
    
    # TODO group by for_query:list of responses
    def on_response_func(for_query, request, response):
        ret.append((for_query, request, response))
    
    pool = RequestThreadPool(http_factory, on_response_func)    
    with pool:
        for q in queries:
            pool.put_request(q)
        pool.join()
    
    return ret



#def _pretty_print_batch_query_responses(resps):
#    for query, response_book in resps.items():
#        print '\n==============='
#        print query
#        for i, response_page in enumerate(response_book):
#            print 'PAGE', i
#            pprint(response_page['response'])    

def _pretty_print_response(for_query, request, response):
    print '\n============='
    print for_query
    print 'REQUEST',
    pprint(request)
    print 'RESPONSE',
    pprint(response)
    
        
                

    
    
def _test_batch_query(youtube, http_factory):
    queries = []
    for i in range(20):
    #request_function, kwargs, http=None, MAX_ITEMS=-1
        queries.append(Query(youtube.channels().list, 
                {"mine":True, "part":"contentDetails"}))
    
    
    resps = batch_query(http_factory, queries)
    for response in resps:
        _pretty_print_response(*response)

def _test_batch_query_paging(youtube, http_factory):
    queries = []
    
    for i in range(5):
        queries.append(Query(youtube.playlistItems().list, 
                {"part":"snippet", "playlistId":"UUVtt6C8Qu_ia7g2l80sY2kQ",
                "maxResults":"2",
                "fields":"items/snippet,nextPageToken"},
                MAX_ITEMS=5))
    
    
    resps = batch_query(http_factory, queries)
    for response in resps:
        _pretty_print_response(*response)

def _test_chain_query(youtube, http_factory):
    #TODO complete
    pass

def _test_response_stream(youtube, http_factory):
    queries = [Query(youtube.playlistItems().list, {"part":"snippet",
                           "maxResults":"2",
                           "playlistId":"UUVtt6C8Qu_ia7g2l80sY2kQ",
                           "fields":"items/snippet,nextPageToken"},
                           MAX_ITEMS=10)]

    def on_response_func(for_query, request, response):
        _pretty_print_response(for_query, request, response)
    
    pool = RequestThreadPool(http_factory, on_response_func)    
    with pool:
        # Put requests into task queue
        for q in queries:
            pool.put_request(q)
        
        pool.join()

def main(argv):
    logging.basicConfig()
    logging.getLogger().setLevel("ERROR")

    CLIENT_SECRETS_FILE = "../data/client_secrets.json"
    SCOPES = "https://www.googleapis.com/auth/youtube"
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    credentials = acquire_credentials(SCOPES, CLIENT_SECRETS_FILE)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))
    
    http_factory = authorized_http_factory(credentials)
    #_test_batch_query(youtube, http_factory)
    #_test_batch_query_paging(youtube, http_factory)
    _test_response_stream(youtube, http_factory)
    





if __name__ == "__main__":
    main(sys.argv)
