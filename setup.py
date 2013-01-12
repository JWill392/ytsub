#  setup.py
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

from ytsub import __version__
from setuptools import setup

setup(
    name='ytsub',
    author='Jackson Williams',
    author_email='jackson.r.williams+ytsub@gmail.com',
    version=__version__,
    packages=['ytsub'],
    license='LICENSE.txt',
    description='List your Youtube subscription videos',
    long_description=open('README.txt').read(),
    install_requires=[
        "google-api-python-client >= 1.0"
    ],
    url = 'https://github.com/jwill392/ytsub',
    entry_points = {
        'console_scripts':
            ['ytsub = ytsub.main:main']},
    package_data = {
        'ytsub':['data/client_secrets.json']
    }
)
