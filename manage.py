#!/usr/bin/env python3
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ddnet_django.settings_private")

    sys.path.append(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'firma_base')
    )

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
