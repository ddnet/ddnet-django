#!/usr/bin/env python3

import os
import sys
import subprocess
from shutil import copyfile
from tempfile import TemporaryDirectory

def fix():
    with TemporaryDirectory() as tempdir:

        for line in sys.stdin:
            m = line.strip('\n')
            copyfile(m, os.path.join(tempdir, os.path.basename(m)))

        p = subprocess.Popen(
            ['map_fix_final', tempdir],
            stdout=sys.stdout,
            stderr=sys.stderr
        )

    return p.wait()

exit(fix())
