#  setup.py
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

from distutils.core import setup

setup(
    name='youtube-list',
    author='Jackson Williams',
    author_email='jackson.r.williams+youtube-list@gmail.com',
    version='0.1.0',
    packages=['youtubelist', 'youtubelist.test'],
    license='LICENSE.txt',
    description='List your Youtube subscription videos',
    long_description=open('README.txt').read(),
    install_requires=[
        "google-api-python-client >= 1.0"
    ],
)
