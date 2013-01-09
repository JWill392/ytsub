#  test_batch.py
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

import unittest
import httplib2
import ytsub
import logging

from pprint import pprint
from threading import RLock

from ytsub.video import Vid
from ytsub.batch import get_http_factory
from ytsub.batch import Query
from ytsub.batch import RequestThreadPool
from ytsub.batch import batch_query
from ytsub.credentials import acquire_credentials
from ytsub.main import setup

# TODO use mocks, assertions

# TODO make this accept a function(request):response instead of predefined [response]
class HttpMockSequence(object):
  '''Mock of httplib2.Http
  '''

  def __init__(self, iterable):
    '''
    Args:
      iterable: iterable, a sequence of pairs of (headers, body)
    '''
    self._iterable = iterable
    self.follow_redirects = True

  def request(self, uri,
              method='GET',
              body=None,
              headers=None,
              redirections=1,
              connection_type=None):
    resp, content = self._iterable.pop(0)
    if content == 'echo_request_headers':
      content = headers
    elif content == 'echo_request_headers_as_json':
      content = simplejson.dumps(headers)
    elif content == 'echo_request_body':
      if hasattr(body, 'read'):
        content = body.read()
      else:
        content = body
    elif content == 'echo_request_uri':
      content = uri
    return httplib2.Response(resp), content

def _pretty_print_response(for_query, request, response):
    print '\n============='
    print for_query
    print 'REQUEST', request['function'].__name__
    pprint(request['kwargs'])
    print 'RESPONSE',
    pprint(response)
    
#TODO cleanup        
youtube, credentials = setup()

        
          
          


# some use cases: 
# NOTE response = (query, request, response) (request is a page of a query)
# NOTE three elements:  1. Query Gen - subs in data from pre-reqs to create a query
#                       2. Query     - is created by QGEN. Could be multiple with diff params
#                       3. Response  - (for_query, request(page of query), response). Could be multiple for query (paging)
# NOTE Given one, can obtain others:  1 <--> 2 <--> 3
# WAIT, actually there's another. Item.  
# Query Gen could make multiple queries per response (eg one per item).  So here's a question.  How to uniquely identify Querys?  Okay, step back a second.  Why do we want to uniquely identify queries? TODO 
# Right now I want to consider the datastructure that will hold each response.  Pushed into once per on_response_func()
       
          
# NOTE I'd like to be able to join together diff query flows -- use as prerequisites.
# EXAMPLE: Fetching watched_videos is a two-step process I see myself using in several larger query flows.  And I don't want to rewrite it every time.
# BUT: This brings up another question of merging dependencies.  That is, WATCHED_VIDEOS_FLOW and MARK_WATCHED_FLOW share a step (fetch my playlist ids).  If both of these joined into a flow, I'd want them to know automatically that they can share step 1.
class TestBatch(unittest.TestCase):
    def test_chain_query(self):
        '''Query dependencies.  For example:
                q1 is used as input for q2 and q3.  
                q2 is input for q4.  
                q4 and q3 are input for q5, the output'''
        
       #HOW I WANT IT TO WORK
        # TODO okay, this structure won't work with multiple requirements.  Perhaps instead of the .single_item and .each_item pre-made functions, we simply make the user write a _on_response function.  It's the basic stupid solution, so we'll see how it works out.

        

        #ROOT
        get_playlists = (youtube.channels().list, 
                                 {'mine':True,
                                  'part':'contentDetails'})
        
        get_watched = flow.add(youtube.playlistItems().list,
                               {'playlistId':'{history_id}',
                                'part':'id',
                                'fields':"items(id,kind),nextPageToken"},
                               MAX_ITEMS=100,
                               history_id=get_playlists.single_item(index=("contentDetails",
                                                                    "relatedPlaylists","watchHistory")))
        #ROOT
        sub_channels = flow.add(youtube.subscriptions().list, 
                                {'mine':True,
                                 'part':'snippet',
                                 'order':'unread',
                                 'fields':'items/snippet,nextPageToken'})
        
        # TODO ability to not query certain subs -- probably would mean letting user implement a (added flow).each_item type function.  Or perhaps one could accept a filterfunc
        upload_ids = flow.add(youtube.channels().list,
                              {'id': '{sub_channel_id}',
                               'part':'contentDetails',
                               'fields':'items/contentDetails'},
                              sub_channel_id=sub_channels.each_item(index=('snippet','resourceId','channelId')))
         
         uploaded_vids = flow.add(youtube.playlistItems().list,
                                  {'playlistId':'{upload_id}',
                                   'part':'snippet'},
                                  MAX_ITEMS=10,
                                  upload_id=upload_ids.single_item(index=('contentDetails','relatedPlaylists',
                                                                          'uploads')))
         
         vid_stats = flow.add(youtube.videos().list,
                              {'id':'{vid_ids}',
                               'part':'statistics'} #TODO this won't do.
                              vid_ids=uploaded_vids.all_batch(50, index=('snippet','resourceId','videoId'))
        #single_item asserts only one item in response -- pretty common pattern in youtube apis
        
        query_response = {}
        gen_query = {}
        
        
        def on_response_func(for_query, request, response):
            kwargs = {'for_query': for_query,
                      'request'  : request,
                      'response' : response}
                      
            query_response[for_query]['by_request'] [request] = kwargs
            query_response[for_query]['by_response'][response] = kwargs
            #TODO Jan 7, 9AM: was mocking this up to see how datastructures would be structured. q_resp and gen_q just written
                
            for gen in generators:
                q = gen(for_query, request, response)
                if q is not None:
                    gen_query[gen]['by_query']   [for_query] = q
                    gen_query[gen]['by_request'] [request]   = q
                    gen_query[gen]['by_response'][response]  = q
                    
                    
        
        #TODO realify
        pool = RequestThreadPool(get_http_factory(credentials), on_response_func)    
        with pool:
            pool.put_request(build_dependent_query({}, 'sub_channels'))
            pool.put_request(build_dependent_query({}, 'my_playlists'))
            pool.do_processing()
        
        print "=============\n==WATCHED ==\n============"
        for resp in resps['watched_videos']:
            _pretty_print_response(*resp)
        print "=============\n==SUB VIDS==\n============"
        for resp in resps['uploaded_videos']:
            _pretty_print_response(*resp)

        #uploaded_video_ids = []
        #for playlist_video in resp['items']:
        #    uploaded_video_ids.append(Vid(sub_channel_author, playlist_video))
        #for vid in uploaded_video_ids:
        #    print vid









    def test_batch_query(self):
        return
        queries = []
        for i in range(20):
        #request_function, kwargs, http=None, MAX_ITEMS=-1
            queries.append(Query(youtube.channels().list, 
                    {'mine':True, 'part':'contentDetails'}))
        
        
        resps = batch_query(get_http_factory(credentials), queries)
        for response in resps:
            _pretty_print_response(*response)

    def test_batch_query_paging(self):
        return
        queries = []
        
        for i in range(5):
            queries.append(Query(youtube.playlistItems().list, 
                    {'part':'snippet', 'playlistId':'UUVtt6C8Qu_ia7g2l80sY2kQ',
                    'maxResults':'2',
                    'fields':'items/snippet,nextPageToken'},
                    MAX_ITEMS=5))
        
        
        resps = batch_query(get_http_factory(credentials), queries)
        for response in resps:
            _pretty_print_response(*response)

    def test_response_stream(self):
        return
        queries = [Query(youtube.playlistItems().list, {'part':'snippet',
                               'maxResults':'2',
                               'playlistId':'UUVtt6C8Qu_ia7g2l80sY2kQ',
                               'fields':'items/snippet,nextPageToken'},
                               MAX_ITEMS=10)]

        def on_response_func(for_query, request, response):
            _pretty_print_response(for_query, request, response)
        
        pool = RequestThreadPool(get_http_factory(credentials), on_response_func)    
        with pool:
            # Put requests into task queue
            for q in queries:
                pool.put_request(q)
            
            pool.do_processing()

def main():
    logging.getLogger().setLevel('INFO')
    unittest.main()

if __name__ == '__main__':
    main()
