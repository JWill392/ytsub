=====
ytsub
=====

ytsub provides a command-line interface to do things with your Youtube subscriptions. You might find it most useful for filtering those
videos using grep, or setting up an auto-downloader using the excellent
youtube-dl. An example usage might look like this::

    $ ytsub list | grep 'FTB\|Feed The Beast' | awk -F"\t" '{print $2}' | tee >(youtube-dl -a /dev/stdin >/dev/tty) | ytsub mark-watched

The above gets list of all unwatched subscription videos, filters out ones that don't include the string 'FTB' or 'Feed The Beast' in their titles, gets youtube-dl to start downloading them, and marks them as watched.


install
=======

ytsub is in PyPI, so you can install it with::

    $ pip install ytsub --upgrade

If you don't have pip, on Ubuntu, you can install it with::

    $ sudo apt-get install python-pip

For other operating systems, see here: http://pypi.python.org/pypi/pip
