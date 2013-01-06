#  credentials.py
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

from os.path import expanduser
from os import pathsep
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run

def acquire_credentials(scopes, secrets_path):
    flow = flow_from_clientsecrets(secrets_path,
      message="Missing client secrets file",
      scope=scopes)

    
    storage = Storage(expanduser("~") + "/.ytsub-oauth2.json")
    credentials = storage.get()

    if credentials is None or credentials.invalid:
      credentials = run(flow, storage)

    return credentials