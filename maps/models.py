from django.db import models
import enum

from ddnet_base.validtors import image_validator

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

class RELEASE(enum.Enum):
    NOT_STARTED = 0
    PENDING = 1
    DONE = 2
    FAILED = 3


def map_name(instance, filename):
    return 'maprelease/' + instance.name + '.map'


class MapRelease(models.Model):
    name = models.CharField(max_length=128, unique=True)
    ddmap = models.FileField('map', upload_to=map_name)
    img = models.ImageField(upload_to='maprelease', validators=[image_validator(1440, 900)])

    server_type = models.ForeignKey(ServerType, on_delete=models.DO_NOTHING)
    stars = models.IntegerField(default=0, choices=STARS)

    release_date = models.DateTimeField()
    release_state = models.IntegerField(
        default=0, choices=((v.value, n) for n, v in RELEASE.__members__.items())
    )

    def __str__(self):
        return self.name


class Map(models.Model):
    name = models.CharField('Map', max_length=128, primary_key=True)
    server_type = models.ForeignKey(
        name='Server', to=ServerType, to_field='name', on_delete=models.DO_NOTHING
    )
    mapper = models.CharField(max_length=128)
    points = models.IntegerField(default=0)
    stars = models.IntegerField(default=0, choices=STARS)
    timestamp = models.DateTimeField('TimeStamp')

    def __str__(self):
        return self.name
