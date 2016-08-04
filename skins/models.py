'''Models for the skindatabase.'''

from datetime import datetime
from django.db import models


class Skin(models.Model):
    '''The model for a Teeworlds-Skin.'''

    name = models.CharField(unique=True, max_length=23)
    creator = models.CharField(max_length=15)
    pack = models.CharField(max_length=64)
    release_date = models.DateTimeField(default=datetime.now)
    skin_image = models.ImageField(upload_to='skins')

    searchfields = [
        'name',
    ]

    list_filter = [
        'pack',
        'creator',
    ]

    def __str__(self):
        '''Stringrepresentation of this model.'''
        return self.name

    class Meta:
        '''Metaoptions.'''

        ordering = ['name']
