# DDNet Django

[![DDraceNetwork](https://ddnet.tw/ddnet-small.png)](https://ddnet.tw)
[![django](http://www.dreamincode.net/forums/uploads/monthly_10_2014/post-659421-141328499356.png)](https://www.djangoproject.com/)

## Installation

1. Install [`Python 3.X`](https://www.python.org/downloads/)
2. `pip install django` will install the newest Django version
3. Navigate to `ddnet-django/ddnet_django/`
4. Create `settings_private.py` file and fill there the following database configuration - replace values between `<` `>` with your individual settings

```python
DEBUG = True
ALLOWED_HOSTS = []
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '$$$django%ddnet%secret123123!!'
# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': '<django.db.backends.postgresql>',
        'NAME': '<ddnet_db>',
        'USER': '<postgres>',
        'PASSWORD': '<postgres>',
        'HOST': '<localhost>',
        'PORT': '<5432>',
    }
}
```
5. Navigate back to the root directory `ddnet-django/`
4. `python manage.py makemigrations` will create a db-scpecific script to upgrade your database
5. `python manage.py migrate` will upgrade your database with the most up-to-date changes
6. `python manage.py runserver runserver [host:port]` will start the application on a default [http://127.0.0.1:8000/](http://127.0.0.1:8000/) server or [http://host:port/](http://host:port/) if you specify the optional parameters


## Contributing


## History


## Credits
- @H-M-H
- @kchaber

## License