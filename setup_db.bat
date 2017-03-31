:: setup django-internal stuff
python manage.py migrate

:: migrations for all the apps
python manage.py makemigrations maps
python manage.py makemigrations servers
python manage.py makemigrations skins

:: create tables
python manage.py migrate maps --database=ddnet_db
python manage.py migrate servers
python manage.py migrate skins --database=skins_db

:: load fixtures for maps app
python manage.py loaddata MapCategory.json  ServerType.json --database=ddnet_db