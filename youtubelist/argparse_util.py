#  argparse_util.py
#  This file is part of youtube-dl 
# 
#  Copyright (C) 2013 - Jackson Williams

#  youtube-dl is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  youtube-dl is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with youtube-dl.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import sys

class ListOrStdinAction(argparse.Action):
    '''This stores a list, taking input from args or stdin if no args.  If '''

    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 type=None,
                 required=False,
                 help=None,
                 metavar=None):
        if default is not None and required is True:
            raise ValueError('If required, default cannot be set; this action'
                             'reads from stdin if given no parameters.')
        
        super(ListOrStdinAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs='*',
            default=default,
            type=type,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = []
        
        if (not self.required and len(values) is 0) or (self.required and values is None):
            for line in sys.stdin:
                items.append(parser._get_value(self, line))
            setattr(namespace, self.dest, items)
            return
        
        items.extend(values)
        setattr(namespace, self.dest, items)
