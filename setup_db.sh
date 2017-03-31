#!/bin/sh

# setup django-internal stuff
./manage.py migrate

# migrations for all the apps
./manage.py makemigrations maps
./manage.py makemigrations servers
./manage.py makemigrations skins

# create tables
./manage.py migrate maps --database=ddnet_db
./manage.py migrate servers
./manage.py migrate skins --database=skins_db

# load fixtures for maps app
./manage.py loaddata MapCategory.json  ServerType.json --database=ddnet_db
