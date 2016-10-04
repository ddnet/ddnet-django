from datetime import datetime
from enum import Enum, unique

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


@unique
class ServerType(Enum):
    NOVICE = 'N'
    MODERATE = 'M'
    BRUTAL = 'B'
    OLDSCHOOL = 'O'
    SOLO = 'S'
    DUMMY = 'D'
    DDMAX = 'DD'
    RACE = 'R'


class MapRelease(models.Model):
    '''The model for a MapRelease'''

    name = models.CharField(max_length=100)
    definition = models.FileField(upload_to='mapreleases/definitions')
    screenshot = models.ImageField(upload_to='mapreleases/screens')
    tml = models.FileField(editable=False, upload_to='mapreleases/tmls')
    stars = models.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(5)
        ]
    )
    server_type = models.CharField(
        max_length=2,
        choices=((x.value, x.name.title()) for x in ServerType),
        default=ServerType.NOVICE.value
    )
    release_date = models.DateTimeField(default=datetime.now)
