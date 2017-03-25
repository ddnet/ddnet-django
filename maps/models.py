from django.db import models
from django.core.exceptions import ValidationError
import enum

from ddnet_base.validtors import image_validator
from ddnet_django.storage import get_valid_name

from .fields import MapFileField, MapImageField

STARS = (
    (0, '☆☆☆☆☆'),
    (1, '★☆☆☆☆'),
    (2, '★★☆☆☆'),
    (3, '★★★☆☆'),
    (4, '★★★★☆'),
    (5, '★★★★★'),
)


class ServerType(models.Model):
    name = models.CharField(unique=True, max_length=32)
    offset = models.IntegerField()
    multiplier = models.IntegerField()

    def __str__(self):
        return self.name

class PROCESS(enum.Enum):
    NOT_STARTED = 0
    PENDING = 1
    DONE = 2
    FAILED = 3


class MapCategory(models.Model):
    name = models.CharField(max_length=64)
    order = models.IntegerField()

    def __str__(self):
        return self.name


def validate_mapname(name):
    valid_name = get_valid_name(name)
    if name != valid_name:
        raise ValidationError('{} is not a valid Mapname, try {} instead.'.format(name, valid_name))


class MapRelease(models.Model):
    name = models.CharField(max_length=128, unique=True, validators=[validate_mapname])
    mapfile = MapFileField(upload_to='mapreleases')
    mapper = models.CharField(max_length=128, blank=True)
    img = MapImageField(upload_to='mapreleases', validators=[image_validator(1440, 900)])

    server_type = models.ForeignKey(ServerType, on_delete=models.DO_NOTHING)
    categories = models.ManyToManyField(to=MapCategory, blank=True)

    stars = models.IntegerField(default=0, choices=STARS)

    release_date = models.DateTimeField()
    release_state = models.IntegerField(
        default=0, choices=((v.value, n) for n, v in PROCESS.__members__.items())
    )
    log = models.TextField(default='', blank=True, editable=False)

    class Meta:
        permissions = (('can_release_map', 'Can release maps'),)

    def __str__(self):
        return self.name


class Map(models.Model):
    name = models.CharField(db_column='Map', max_length=128, primary_key=True)
    server_type = models.ForeignKey(
        db_column='Server', to=ServerType, to_field='name', on_delete=models.DO_NOTHING
    )
    categories = models.ManyToManyField(to=MapCategory, blank=True)
    mapper = models.CharField(db_column='Mapper', max_length=128, blank=True)
    points = models.IntegerField(db_column='Points', default=0)
    stars = models.IntegerField(db_column='Stars', default=0, choices=STARS)
    timestamp = models.DateTimeField(db_column='Timestamp', blank=True)

    class Meta:
        db_table = 'record_maps'
        managed = False

    def save(self, *args, **kwargs):
        self.points = self.stars * self.server_type.multiplier + self.server_type.offset
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class MapFix(models.Model):
    ddmap = models.ForeignKey(Map)
    mapfile = MapFileField(upload_to='mapfixes')
    fix_state = models.IntegerField(
        default=0, choices=((v.value, n) for n, v in PROCESS.__members__.items())
    )
    log = models.TextField(default='', blank=True, editable=False)

    @property
    def name(self):
        return self.ddmap.name

    def __str__(self):
        return self.name
