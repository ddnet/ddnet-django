from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


import os

from .models import MapRelease, MapFix


@receiver(post_delete, sender=MapRelease)
def post_map_release_delete(sender, instance, **kwargs):
    instance.mapfile.storage.delete(instance.mapfile.name)
    instance.img.storage.delete(instance.img.name)


@receiver(post_save, sender=MapRelease)
def post_map_release_save(sender, instance, **kwargs):
    changed = False

    filename = instance.mapfile.field.generate_filename(instance, instance.name)
    if filename != instance.mapfile.name:
        try:
            os.rename(instance.mapfile.path, instance.mapfile.storage.path(filename))
        except FileNotFoundError:
            pass
        instance.mapfile.name = filename
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


@receiver(post_delete, sender=MapFix)
def post_map_fix_delete(sender, instance, **kwargs):
    instance.mapfile.storage.delete(instance.mapfile.name)


@receiver(post_save, sender=MapFix)
def post_map_fix_save(sender, instance, **kwargs):
    filename = instance.mapfile.field.generate_filename(instance, instance.name)
    if filename != instance.mapfile.name:
        try:
            os.rename(instance.mapfile.path, instance.mapfile.storage.path(filename))
        except FileNotFoundError:
            pass
        instance.mapfile.name = filename
        instance.save()
