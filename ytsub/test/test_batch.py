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

#TODO TODO TODO was here
#class _QueryFlowNode:
#    def __init__(

#class QueryFlow:
#    def __init__(self,):
#        self.
#    def inject(pool):
#        '''Invoked within with pool (instance of RequestThreadPool)
#        Injects queries from this flow that have no pre-requisite queries.'''
        
          
          
          
          
# NOTE I'd like to be able to join together diff query flows -- use as prerequisites.
# EXAMPLE: Fetching watched_videos is a two-step process I see myself using in several larger query flows.  And I don't want to rewrite it every time.
# BUT: This brings up another question of merging dependencies.  That is, WATCHED_VIDEOS_FLOW and MARK_WATCHED_FLOW share a step (fetch my playlist ids).  If both of these joined into a flow, I'd want them to know automatically that they can share step 1.
class TestBatch(unittest.TestCase):
    def test_chain_query(self):
        '''Query dependencies.  For example:
                q1 is used as input for q2 and q3.  
                q2 is input for q4.  
                q4 and q3 are input for q5, the output'''
        
        query_children = {'my_playlists':['watched_videos'],
                          'sub_channels':['channel_upload_id'],
                          'channel_upload_id':['uploaded_videos']}
        
        # TODO Multiplicity. This doesn't work if we want to get vids from /all/ subs.  it only gets from one.
        # Will need to specify if we need to wait for every page, or can do for each page individually
        # TODO turn into class.  QueryFlow, perhaps.  Consider DSL for dependencies.

        
        def build_dependent_query(req_resps, query_id):
            if query_id is 'my_playlists':
                q = Query(youtube.channels().list,
                          {'mine':True,
                           'part':'contentDetails'},
                          name=query_id)
                          
            elif query_id is 'watched_videos':
                history_id = req_resps['my_playlists']["items"][0] \
                                      ["contentDetails"]["relatedPlaylists"] \
                                      ["watchHistory"]
            
                q = Query(youtube.playlistItems().list,
                          {'playlistId':history_id,
                           'part':'id',
                           'fields':"items(id,kind),nextPageToken"},
                          MAX_ITEMS=100,
                          name=query_id)
            
            elif query_id is 'sub_channels':
                q = Query(youtube.subscriptions().list, 
                          {'mine':True,
                           'part':'snippet',
                           'order':'unread',
                           'fields':'items/snippet,nextPageToken'},
                          MAX_ITEMS=1,
                          name=query_id)
                             
                             
            elif query_id is 'channel_upload_id':
                sub_channel_id = req_resps['sub_channels']['items'][0]['snippet']['resourceId']['channelId']
                
                q = Query(youtube.channels().list,
                             {'id': sub_channel_id,
                              'part':'contentDetails',
                              'fields':'items/contentDetails'},
                             MAX_ITEMS=1,
                             name=query_id)
                
                
            elif query_id is 'uploaded_videos':
                channel_upload_id = req_resps['channel_upload_id']['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                q = Query(youtube.playlistItems().list,
                                  {'playlistId':channel_upload_id,
                                   'part':'snippet'},
                                  MAX_ITEMS=10,
                                  name=query_id)
            else:
                raise ValueError('Query id {qid} does not exist'.format(qid=query_id))
            
            logging.getLogger().debug('chain query: adding next query: ' + q.get_name())
            return q
        
        resps = {}
        resps_lock = RLock()
        
        def on_response_func(for_query, request, response):
            for_name = for_query.get_name()
            child_queries = query_children.get(for_name)

            with resps_lock:
                if resps.get(for_name) is None:
                    resps[for_name] = [(for_query, request, response)]
                else:
                    resps[for_name].append((for_query, request, response))

            if child_queries is None:
                print 'END!'
                return
            
            for cq_name in child_queries:
                #TODO should prolly include request for paging
                next_query = build_dependent_query({for_name:response}, cq_name)
                
                pool.put_request(next_query)
        
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
