import re

from django.core.files.storage import FileSystemStorage
from django.utils.encoding import force_text


def get_valid_name(name):
    s = force_text(name).strip()
    return re.sub(r'(?u)[^-+\w()\[\]\{\}=~!\'&#, .]', '', s)

class DDNetFileSystemStorage(FileSystemStorage):

    def get_valid_name(self, name):
        return get_valid_name(name)
