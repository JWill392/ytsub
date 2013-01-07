       #HOW I WANT IT TO WORK
        # TODO okay, this structure won't work with multiple requirements.  Perhaps instead of the .single_item and .each_item pre-made functions, we simply make the user write a _on_response function.  It's the basic stupid solution, so we'll see how it works out.
        flow = QueryFlow()
        #ROOT
        get_playlists = flow.add(youtube.channels().list, 
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
