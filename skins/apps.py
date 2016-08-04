'''Skinsapp.'''

from django.apps import AppConfig


class SkinsConfig(AppConfig):
    '''Some appmetadata.'''

    name = 'skins'

    def ready(self):
        # this import is required here and registers signals once the skins app is loaded
        import skins.signals
        pass
