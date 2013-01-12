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
from ytsub.video import Vid
from datetime import datetime
from datetime import timedelta


import random
import os
import Queue
import httplib2
import logging
import sys
import threading
import time
import collections

#TODO use priority queue.  In cmd-line application, would allow us to stream output (useful for using with pipes, if some other time-intensive task uses this as input).  Prioritize depth-first rather than bredth-first.  Perhaps just a bool option?  I dunno when you'd want bredth rather than depth first, though.
# NOTE the problem with this is if we wanted to sort the output.  BUT the unix philosophy says we shouldn't.  A tool like sort should do that. Which is convenient for streaming output!

#TODO Batch requests.  Ugh, just found out this exists: https://developers.google.com/api-client-library/python/guide/batch . I don't think it obviates the need for RequestThreadPool, but it does get rid of a lot of the usecases.  Basically the only time you'd need a thread pool is with query dependencies like paging and chaining.
# So to utilize batching, the first query should have everything batched together.  Then as more requests get added to the queue, we can batch them together and send them.

#TODO switch to using the preexisting list_next methods

# How many threads to use
NUM_THREADS = 3

class QueryLimit:
    '''Tells a Query when to stop paging.
    Called after each request, and once before first request.
    Guaranteed to run once per response, even if already done.
        |-> Useful to remove response items that are outside limit.'''
    def __call__(self, for_query, request, response):
        pass

class QueryLimitCount(QueryLimit):
    def __init__(self, MAX_ITEMS):
        self._MAX_ITEMS = MAX_ITEMS
        self._item_count = 0
    
    def __call__(self, for_query, request, response):
        if self._MAX_ITEMS == -1:
            return
    
        # prevent last fetch overshoot
        for_query._kwargs['maxResults'] = \
                min(int(for_query._kwargs['maxResults']), self._MAX_ITEMS - self._item_count)
        
        # first call -- still want to set maxResults
        if response is None:
            return
            
        try:
            self._item_count += len(response['items'])
        except KeyError:
            return # no items
            
        # done if item max reached
        if self._item_count == self._MAX_ITEMS:
            for_query._done = "received MAX_ITEMS items (%i)" % self._item_count

class QueryLimitAge(QueryLimit):
    def __init__(self, MAX_AGE):
        self._active = (MAX_AGE != -1)
        if not self._active:
            return
            
        self._cutoff_date = datetime.now() - timedelta(MAX_AGE+1) #days
        
    def __call__(self, for_query, request, response):
        if not self._active:
            return
        
        # Nothing to do before first response
        if response is None:
            return
        
        def within_cutoff(vid):
            v = Vid(None,vid)
            if v.date < self._cutoff_date:
                return False
            return True
        

        
        # remove videos outside of cutoff
        vids_before_filter = len(response['items'])
        response['items'][:] = [i for i in response['items'] if within_cutoff(i)]    
        # NOTE, using list slice in order to remove from response, not just make new copy        
        
        if vids_before_filter != len(response['items']):
            return
        


class Query:
    def __init__(self, request_function, kwargs, limit=QueryLimit(), name=''):
        self._request_function = request_function
        self._done = ''
        self._name = name
        
        # accept multiple limit functions -- and ensure singles are iterable
        if not isinstance(limit, collections.Iterable):
            limit = (limit,)
        self._limit = limit
        
        # adjusted down later if MAX_ITEMS less than 50
        if 'maxResults' not in kwargs:
            kwargs['maxResults'] = 50
        self._kwargs = kwargs
        
        # setup for first call to limit -- before first request
        self._last_response = (self, self.get_last_request(), None)

        # call each limit once before starting
        for l in self._limit:
            l(*self._last_response)
    
    def get_name(self):
        return self._name
    
    #TODO raise error if haven't yet called next
    def get_last_request(self):
        return {'function':self._request_function,
                'kwargs':deepcopy(self._kwargs)}
    
    def request_next_page(self, http):
        if self._done:
            raise StopIteration(self._done)
    
        if http is None:
            raise ValueError("http is None")
    
        # send REST API request and wait for response
        response = self._request_function(**self._kwargs).execute(http=http)
        self._last_response = (self, self.get_last_request(), response)
           
        # run limits
        for l in self._limit:
            l(*self._last_response)
        
        # if a limit says done, no need to check exhausted
        if self._done:
            return response 
        
        # done if server exhausted (no more items avail)
        if 'nextPageToken' not in response:
            self._done = "Server has no more items"
            return response
        
        # not done; page query kwargs
        self._kwargs["pageToken"] = response["nextPageToken"]
        return response
   

def _clear_queue(queue):
    try:
        while queue.get(block=False):
            pass
    except Queue.Empty:
        pass
    while queue.unfinished_tasks > 0:
        queue.task_done()

def _queue_not_done(queue):
    return (not queue.empty()) or (queue.unfinished_tasks is not 0)

class RequestThreadPool:
    """Creates a thread pool to process api requests.
    Used with with statement.  Call do_processing before end of with."""
    def __init__(self, authorized_http_factory, on_response_func, thread_count=NUM_THREADS):
        self._http_factory = authorized_http_factory
        self._THREAD_COUNT = thread_count
        self._on_response_func = on_response_func

        self._request_queue = Queue.Queue()
        self._response_queue = Queue.Queue()
        
        self._exit_event = threading.Event()
        self._req_threads = []
        self._resp_thread = threading.current_thread()
        
        for i in range(self._THREAD_COUNT):
            req_thread = threading.Thread(target=self._process_requests)
            req_thread.daemon = True
            self._req_threads.append(req_thread)
        
    
    def put_request(self, request):
        self._request_queue.put(request)
    
    # TODO way for client to decide to __exit__ in on_response_func?
    def do_processing(self):
        # wait until something goes wrong or done all requests and responses
        while _queue_not_done(self._request_queue) or \
              _queue_not_done(self._response_queue):
            if self._exit_event.is_set():
                break
            
            try:
                response = self._response_queue.get(timeout=0.001)
            except Queue.Empty:
                continue
            
            logging.getLogger().debug("Response received: " + str(response))
            self._on_response_func(*response)
            self._response_queue.task_done()
        
    def _process_requests(self):
        http = self._http_factory()

        while not self._exit_event.is_set():
            try:
                query = self._request_queue.get(timeout=0.001)
            except Queue.Empty:
                continue
            
            http_failures = 0
            while True: # retry executing query
                try:
                    while True: # execute query with autopaging
                        response = query.request_next_page(http)
                        self._response_queue.put((query, query.get_last_request(), response))
                        http_failures -= 1
                except StopIteration: #successfully got every page
                    self._request_queue.task_done()
                    break
                except HttpError, e:
                    if http_failures > 8: # TODO write testcase for this -- have never executed this code
                        logging.getLogger().critical("Http requests failed too many times.  Exiting. " + str(e))
                        self.__exit__(*sys.exc_info())
                        break
                    http_failures += 1
                    logging.getLogger().info("Increasing backoff, got status code: %d" % e.resp.status)
                    time.sleep((2 ** http_failures) * 0.1 * (random.random() * 0.1 + 0.95))
                except Exception, e:
                    logging.getLogger().critical("Unexpected error in process_requests thread. Exiting. " + str(e))
                    self.__exit__(*sys.exc_info())
                    break
        logging.getLogger().debug('Exiting _process_requests thread')  
                    
    
    
    def __enter__(self):
        for t in self._req_threads:
            t.start()
        
        return self
    
    
    def __exit__(self, exc_type, exc_value, traceback):
        logging.getLogger().debug('Exiting RequestThreadPool: type:{t} value:{v} traceback:{tr}'
                                  .format(t=exc_type, v=exc_value, tr=traceback))
    
        if self._exit_event.is_set():
            return #someone else is already calling this
            
        # signal all threads to join
        self._exit_event.set()

        logging.getLogger().debug('Signalled RequestThreadPool threads to exit, waiting.')        
        
        # wait for other threads to end
        for t in self._req_threads + [self._resp_thread]:
            if t is threading.current_thread():
                continue
            t.join()
        
        logging.getLogger().debug('RequestThreadPool threads exited, exiting context.')
        
        # cleanup fields set in __enter__
        self._exit_event.clear()
        _clear_queue(self._request_queue)
        _clear_queue(self._response_queue)
        
        return False #Don't supress exceptions

def get_http_factory(credentials):
    return lambda : credentials.authorize(httplib2.Http(cache=".cache"))

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
        pool.do_processing()
    
    return ret



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
    





if __name__ == "__main__":
    main(sys.argv)
