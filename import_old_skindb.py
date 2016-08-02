#!/usr/bin/env python3

'''
This is a small commandlinetool to import skins form the old database to django.

Basically it parses some html and downloads all skins.
'''

import os

from datetime import datetime

from requests import get
import bs4

import django
from django.utils.timezone import get_current_timezone
from django.core.files.base import ContentFile

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ddnet_django.settings")
django.setup()

from skins.models import Skin # noqa - need to setup django first


soup = bs4.BeautifulSoup(get('https://ddnet.tw/skins/').content, 'html.parser')

skin_table = soup.find(name='table')

for tr in skin_table.find_all('tr'):
    try:
        temp = tuple(td for td in tr.find_all('td'))
        _, name, creator, pack, release, download = temp
        name = name.text
        creator = creator.text
        pack = pack.text
        release = release.text
        file_name = download.find('a')['download']
        download = download.find('a')['href']
        print(name, creator, pack, release, file_name, download)

        # create a new skin
        skin = Skin(
            name=name,
            creator=creator,
            pack=pack,
            release_date=get_current_timezone().localize(datetime.strptime(release, '%Y-%m-%d'))
        )

        skin.skin_image.save(file_name,  # get the actual image and save it
                             ContentFile(get('https://ddnet.tw/skins/' + download).content))

        # write it to db
        skin.save()
    except Exception as e: # noqa - yes it is rather ugly
        print(e)
