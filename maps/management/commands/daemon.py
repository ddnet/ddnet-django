import os
import signal
import logging
import argparse
import threading

from django.core.management.base import BaseCommand

from maps.utils import handle_cleanup, handle_scheduled_releases


logging.basicConfig()
logger = logging.getLogger(__name__)


def start():
    run = True

    def keep_running():
        nonlocal run
        return run

    cv = threading.Condition()

    def kill(sig, frame):
        nonlocal cv, run
        run = False
        try:
            with cv:
                cv.notify_all()
        except RuntimeError:
            pass

    signal.signal(signal.SIGTERM, kill)
    t1 = threading.Thread(target=handle_scheduled_releases, args=(cv, keep_running))
    t2 = threading.Thread(target=handle_cleanup, args=(cv, keep_running))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

class Command(BaseCommand):
    help = 'starts and stops daemon responsible for scheduled mapreleases and deleting old logs.'

    def add_arguments(self, parser):
        parser.add_argument('pidfile', type=str)
        parser.add_argument('--force', action='store_true')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--start', action='store_true')
        group.add_argument('--stop', action='store_true')

    def handle(self, *args, **options):

        pidfile = options['pidfile']

        if options['start']:
            with open(pidfile, 'w') as f:
                f.write(str(os.getpid()))
            start()
            os.remove(pidfile)
        else:
            try:
                with open(pidfile, 'r') as f:
                    pid = int(f.readline())
                    if options['force']:
                        os.kill(pid, signal.SIGKILL)
                    else:
                        os.kill(pid, signal.SIGTERM)
            except FileNotFoundError:
                logger.exception('Pidfile not found.')
            except ValueError:
                logger.exception('Could not read pid from pidfile.')
