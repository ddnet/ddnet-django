from threading import Thread

from django.apps import AppConfig

class MapsConfig(AppConfig):
    name = 'maps'

    def ready(self):
        import maps.signals

        from maps.utils import handle_scheduled_releases, handle_cleanup
        t = Thread(target=handle_scheduled_releases)
        t.daemon = True
        t.start()

        t2 = Thread(target=handle_cleanup)
        t2.daemon = True
        t2.start()
