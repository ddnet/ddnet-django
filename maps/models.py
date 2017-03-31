from django.db import models
from django.core.exceptions import ValidationError
import enum
from django.utils import timezone

from ddnet_base.validators import image_validator
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

    class Meta:
        ordering = ('name',)

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

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


def validate_mapname(name):
    valid_name = get_valid_name(name)
    if name != valid_name:
        raise ValidationError('{} is not a valid Mapname, try {} instead.'.format(name, valid_name))

    if Map.objects.filter(pk=name):
        raise ValidationError('The Map {} already exists.'.format(name))


class MapRelease(models.Model):
    name = models.CharField(max_length=128, unique=True, validators=[validate_mapname])
    mapfile = MapFileField(upload_to='mapreleases')
    mapper = models.CharField(max_length=128, blank=True)
    img = MapImageField(upload_to='mapreleases', validators=[image_validator(1440, 900)])

    server_type = models.ForeignKey(ServerType, on_delete=models.DO_NOTHING)
    categories = models.ManyToManyField(to=MapCategory, blank=True)

    stars = models.IntegerField(default=0, choices=STARS)

    timestamp = models.DateTimeField(blank=True, auto_now_add=True)
    state = models.IntegerField(
        default=0, choices=((v.value, n) for n, v in PROCESS.__members__.items())
    )

    class Meta:
        permissions = (('can_release_map', 'Can release maps'),)
        ordering = ('name',)

    def to_Map(self):
        return Map(
            name=self.name,
            server_type=self.server_type,
            categories=self.categories.all(),
            mapper=self.mapper,
            stars=self.stars,
            timestamp=timezone.now()
        )

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
        ordering = ('name',)

    def save(self, *args, **kwargs):
        self.points = self.stars * self.server_type.multiplier + self.server_type.offset
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class MapFix(models.Model):
    ddmap = models.ForeignKey(Map)
    mapfile = MapFileField(upload_to='mapfixes')
    state = models.IntegerField(
        default=0, choices=((v.value, n) for n, v in PROCESS.__members__.items())
    )
    timestamp = models.DateTimeField(blank=True, auto_now_add=True)

    class Meta:
        ordering = ('mapfile',)

    @property
    def name(self):
        return self.ddmap.name

    def __str__(self):
        return self.name


class ReleaseLog(models.Model):
    log = models.TextField(default='', blank=True)
    timestamp = models.DateTimeField(auto_now=True)
    state = models.IntegerField(
        default=0, choices=((v.value, n) for n, v in PROCESS.__members__.items())
    )

    class Meta:
        ordering = ('-timestamp',)

    def __str__(self):
        return str(self.timestamp)


class FixLog(models.Model):
    log = models.TextField(default='', blank=True)
    timestamp = models.DateTimeField(auto_now=True)
    state = models.IntegerField(
        default=0, choices=((v.value, n) for n, v in PROCESS.__members__.items())
    )

    class Meta:
        ordering = ('-timestamp',)

    def __str__(self):
        return str(self.timestamp)


class ScheduledMapRelease(models.Model):
    release_date = models.DateTimeField()
    maps = models.ManyToManyField(to=MapRelease)
    broadcast = models.CharField(max_length=128, blank=True)
    state = models.IntegerField(
        default=0, choices=((v.value, n) for n, v in PROCESS.__members__.items())
    )

    class Meta:
        ordering = ('release_date',)

    def __str__(self):
        return str(self.release_date)
