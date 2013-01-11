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

Installing is pretty easy on linux systems
1. Install pip (python package manager) if you don't have it::
    $ sudo apt-get install python-pip
2. Download ytsub.  To get the latest stable release, head to https://github.com/JWill392/ytsub/tags and click one of the download links for the latest tag.
3. Open archive, take out the archive in /dist -- should look like: ytsub-<version number>.tar.gz. Don't uncompress it.
4. Run pip install with the dist archive::
    $ sudo pip install ytsub-<version number>.tar.gz  --upgrade

That's it.  It's runnable like any other command::
    $ ytsub list -c 1 -t 0

Alternatively, you can use git:
    1. sudo apt-get install python-pip git
    2. git clone -b release https://github.com/JWill392/ytsub.git
    3. sudo pip install ytsub/dist/<press tab -- should be just the one dist archive in here> --upgrade
    4. rm -rf ytsub
