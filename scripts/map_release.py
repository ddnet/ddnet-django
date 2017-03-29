#!/usr/bin/env python3

import os
import sys
import json
from shutil import copyfile
from tempfile import TemporaryDirectory
import subprocess

from PIL import Image


def release():
    with TemporaryDirectory() as tempdir:
        maps = json.load(sys.stdin)

        for m, d in maps.items():
            mappath = os.path.join(tempdir, os.path.basename(d['map']))
            copyfile(d['map'], mappath)

            # generate msgpack
            p = subprocess.Popen(
                ['map_properties', mappath, os.path.join(tempdir, m + '.msgpack')],
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            if p.wait() != 0:
                print('map_properties terminated with error.')
                return 1

            # generate img
            impath = os.path.join(tempdir, os.path.basename(d['image']))
            im = Image.open(d['image'])
            im.thumbnail((360, 225))
            im.save(impath)

            p = subprocess.Popen(
                ['zopflipng', '-m', '-y', impath, impath],
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            if p.wait() != 0:
                print('zopflipng terminated with error.')
                return 2

        types_dir = os.path.join(tempdir, 'types')
        os.mkdir(types_dir)
        server_types = set(d['server_type'] for d in maps.values())
        for st in server_types:
            p = subprocess.Popen(
               ['print_mapfile', st],
               stdout=open(os.path.join(types_dir, st.lower()), 'wb'),
               stderr=sys.stderr
            )
            if p.wait() != 0:
                print('print_mapfile terminated with error.')
                return 3

        # ensure tempdir is accessible
        subprocess.call(['chmod', '-R', 'a+r', tempdir])
        p = subprocess.Popen(
            ['map_release_final', tempdir],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        if p.wait() != 0:
            print('map_release_final terminated with error.')
            return 4

    return 0


exit(release())
