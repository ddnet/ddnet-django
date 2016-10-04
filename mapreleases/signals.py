import os

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from ddnet_django.settings import MAPRELEASES_MEDIA_ROOT, MEDIA_ROOT
from mapreleases.models import MapRelease
from mapreleases.tml.tml_generator import TmlGenerator


@receiver(post_save, sender=MapRelease)
def model_pre_save(sender, instance, **kwargs):
    tmp_tml_file = os.path.join(MAPRELEASES_MEDIA_ROOT, 'tmp')
    print(tmp_tml_file)
    tml_generator = TmlGenerator()
    print(tml_generator)
    #TODO: something wrong is with this generator
    #tml_generator.generate(os.path.join(MEDIA_ROOT, instance.definition.name), tmp_tml_file)
