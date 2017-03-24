import re
import os

from django.db.models.fields.files import FileField, FieldFile, ImageField, ImageFieldFile
from django.core.files.storage import default_storage

from ddnet_django.storage import get_valid_name


class MapFileField(FileField):

    def generate_filename(self, instance, filename):
        return self.upload_to + '/maps/' + get_valid_name(instance.name) + '.map'


class MapImageField(ImageField):

    def generate_filename(self, instance, filename):
        return self.upload_to + '/images/' + re.sub('[^a-zA-Z0-9]', '_', instance.name) + '.png'
