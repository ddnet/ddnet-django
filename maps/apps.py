from django.apps import AppConfig

class MapsConfig(AppConfig):
    name = 'maps'

    def ready(self):
        import maps.signals
        pass
