#  test_api.py
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
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run

class TestYoutubeAPI(unittest.TestCase):

    def test_fail(self):
        self.failUnless(False)

def main():
    unittest.main()

if __name__ == '__main__':
    main()