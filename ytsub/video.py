#  video.py
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

from functools import total_ordering
from datetime import datetime
from datetime import timedelta

@total_ordering
class Vid:
    def __init__(self, author_name, playlist_item_video):
        self.id = playlist_item_video["snippet"]["resourceId"]["videoId"]
        self.title = playlist_item_video["snippet"]["title"]
        self.date = datetime.strptime(\
                playlist_item_video["snippet"]["publishedAt"],\
                "%Y-%m-%dT%H:%M:%S.000Z")
        self.author = author_name
        
    def __str__(self):
        return "Vid{id:"+self.id+ \
                ", date:"+self.date.isoformat()+ \
                ", title:"+self.title+ \
                ", author:"+self.author+"}"
        
    def __eq__(self, other):
        return self.id == other.id
        
    def __lt__(self, other):
        return self.date < other.date
        
    def __hash__(self):
        return hash(self.id)
