#!/usr/bin/env python3

import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ddnet_django.settings_private")
django.setup()

from maps.utils import print_mapfile

print_mapfile(sys.argv[1])
