#!/usr/bin/env python3

import os
import sys
import django

sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ddnet-django')
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ddnet_django.settings_private")
django.setup()

from maps.models import MapCategory, Map


categories = {i.name: i for i in MapCategory.objects.all()}

key = None

for line in sys.stdin:
    line = line.strip('\n')

    if line.startswith('───'):
        l = line.strip('───').strip()
        if l in categories.keys():
            key = l
        else:
            key = None
    elif key is not None:
        mp = 'Unknown Mapper'
        try:
            s, m, mp = line.split('|')
        except ValueError:
            try:
                s, m = line.split('|')
            except ValueError:
                continue

        Map.objects.get(pk=m).categories.add(categories[key])
