===========
youtube-list
===========

youtube-list provides a command-line interface to list your Youtube
subscription videos. You might find it most useful for filtering those
videos using grep, or setting up an auto-downloader using the excellent
youtube-dl. An example usage might look like this::

    $ youtube-list | grep 'FTB\|Feed The Beast' | awk '{print $NF}' | tee >(youtube-list --mark-watched &>/dev/null) | youtube-dl -a /dev/stdin

The above gets list of all unwatched subscription videos, filters out ones that don't include the string 'FTB' or 'Feed The Beast' in their titles, gets youtube-dl to start downloading them, and marks them as watched.
