import os
import zipfile
from os.path import basename

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from ddnet_django.settings import SKINS_ZIP_ARCHIVE, MEDIA_ROOT
from skins.models import Skin


@receiver(post_save, sender=Skin)
def model_post_save(sender, instance, **kwargs):
    # call only for skin creation
    if kwargs.get('created', False):
        with zipfile.ZipFile(SKINS_ZIP_ARCHIVE, 'a') as skins_zip:
            curr_skin_path = os.path.join(MEDIA_ROOT, instance.skin_image.name)
            skins_zip.write(curr_skin_path, basename(curr_skin_path))


@receiver(post_delete, sender=Skin)
def model_post_delete(sender, instance, **kwargs):
    tmp_zip_file_path = SKINS_ZIP_ARCHIVE + 'tmp'
    with zipfile.ZipFile(SKINS_ZIP_ARCHIVE, 'r') as skins_zip:
        new_skins_zip = zipfile.ZipFile(tmp_zip_file_path, 'w')
        for item in skins_zip.infolist():
            buffer = skins_zip.read(item.filename)
            if item.filename != basename(instance.skin_image.name):
                new_skins_zip.writestr(item, buffer)
        new_skins_zip.close()
    os.remove(SKINS_ZIP_ARCHIVE)
    os.rename(tmp_zip_file_path, SKINS_ZIP_ARCHIVE)
