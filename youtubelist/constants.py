#  constants.py
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

#TODO improve so additional IDs after a full URL will be detected as probably not intended
#TODO split into multiple, easier to read, regexes
YTL_VIDEO_ID_REGEX = '^(?:(?:(?:http://)?www\.)?youtube\.com/watch\?(\S)*?v=([a-zA-Z0-9_-]{11})[\S]*)$|^([a-zA-Z0-9_-]{11})$'

