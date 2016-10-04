from django.apps import AppConfig


class MapreleasesConfig(AppConfig):
    name = 'mapreleases'

    def ready(self):
        # this import is required here and registers signals once the skins app is loaded
        import mapreleases.signals
        pass
