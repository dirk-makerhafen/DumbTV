DumbTV
======
DumbTV creates TV-like channels from content provided by kodi/xbmc plugins via [kodino](https://github.com/dirk-attraktor/kodino)


### Dependencys:

Requires python2 because all kodi plugins are python2. 

```Shell
apt-get install python python-pip redis-server ffmpeg python-bs4 unzip
```
```Shell
pip install django django_extensions django_widget_tweaks django_crispy_forms redis django-adminlte2 polib HTMLParser BeautifulSoup4
```


### Installation

To install DumbTV, first clone this repository:
```Shell
git clone https://github.com/dirk-attraktor/dumbTV.git
```

Then, clone kodino
```Shell
cd dumpTV
git clone https://github.com/dirk-attraktor/kodino.git
```

Update and upgrade kodino repositorys
```Shell
python kodino/kodinoPlugins.py update
python kodino/kodinoPlugins.py upgrade
```

Install some known good plugins.
```Shell
python install_known_good_plugins.py
```

Create database
```Shell
python manage.py migrate 
```

Create superuser
```Shell
python manage.py createsuperuser
```

### Running

    python manage.py runserver ip:port

open http://ip:port  in Browser

    
