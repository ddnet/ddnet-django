'''
WSGI config for ddnet_django project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
'''

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ddnet_django.settings")

application = get_wsgi_application()


from threading import Thread
from maps.utils import handle_scheduled_releases, handle_cleanup
t = Thread(target=handle_scheduled_releases)
t.daemon = True
t.start()

t2 = Thread(target=handle_cleanup)
t2.daemon = True
t2.start()
