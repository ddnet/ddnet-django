from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

import os

from .models import MapRelease


@receiver(post_delete, sender=MapRelease)
def post_map_release_delete(sender, instance, **kwargs):
    default_storage.delete(instance.ddmap.path)
    default_storage.delete(instance.img.path)


@receiver(post_save, sender=MapRelease)
def post_map_release_save(sender, instance, **kwargs):
    changed = False

    filename = instance.ddmap.field.generate_filename(instance, instance.name)
    if filename != instance.ddmap.name:
        try:
            os.rename(instance.ddmap.path, instance.ddmap.storage.path(filename))
        except FileNotFoundError:
            pass
        instance.ddmap.name = filename
        changed = True

    filename = instance.img.field.generate_filename(instance, instance.name)
    if filename != instance.img.name:
        try:
            os.rename(instance.img.path, instance.img.storage.path(filename))
        except FileNotFoundError:
            pass
        instance.img.name = filename
        changed = True

    if changed:
        instance.save()
