import os
import zipfile

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from os.path import basename

from ddnet_django.settings import SKINS_ZIP_ARCHIVE, MEDIA_ROOT, BASE_DIR
from skins.models import Skin


@receiver(post_save, sender=Skin)
def model_post_save(sender, instance, **kwargs):
    # call only for skin creation
    if kwargs.get('created', False):
        with zipfile.ZipFile(SKINS_ZIP_ARCHIVE, 'a') as skins_zip:
            curr_skin_path = os.path.join(MEDIA_ROOT, instance.skin_image.name)
            skins_zip.write(curr_skin_path, basename(curr_skin_path))


@receiver(post_delete, sender=Skin)
def model_post_delete(sender, **kwargs):
    print('Deleted: {SKIN}')
