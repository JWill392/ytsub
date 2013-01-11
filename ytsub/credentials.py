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

import pkgutil
import tempfile
import oauth2client.clientsecrets as clientsecrets
import oauth2client
import sys

from os.path import expanduser
from os import pathsep
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run

def acquire_credentials(scopes):
    client_secrets_contents = pkgutil.get_data('ytsub','data/client_secrets.json')
    if client_secrets_contents is None:
        sys.exit("Missing clientsecrets.json file.")
    
    try: 
        client_type, client_info = clientsecrets.loads(client_secrets_contents)
        if client_type in [clientsecrets.TYPE_WEB, clientsecrets.TYPE_INSTALLED]: 
            flow = OAuth2WebServerFlow( 
                client_info['client_id'], 
                client_info['client_secret'], 
                scopes, 
                redirect_uri=client_info['redirect_uris'], 
                user_agent=None, 
                auth_uri=client_info['auth_uri'], 
                token_uri=client_info['token_uri']) 
   
    except clientsecrets.InvalidClientSecretsError: 
        sys.exit("Invalid client secrets file.") 

    
    storage = Storage(expanduser("~") + "/.ytsub-oauth2.json")
    credentials = storage.get()

    if credentials is None or credentials.invalid:
      credentials = run(flow, storage)

    return credentials
