import json
import time
import logging
import subprocess
from threading import Thread
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.db.models.functions import Lower
from django.core.exceptions import ObjectDoesNotExist

from ddnet.utils import Log, log_exception

from .models import (
    Map, MapCategory, MapRelease, ReleaseLog, MapFix, FixLog, ScheduledMapRelease, PROCESS
)


logger = logging.getLogger(__name__)

# Global Logs
LOGS = {}

def current_release_log():
    return LOGS.get('release')

def current_fix_log():
    return LOGS.get('fix')


def print_map(m):
    if m.mapper and m.mapper != 'Unknown Mapper':
        print(str(m.stars) + '|' + m.name + '|' + m.mapper)
    else:
        print(str(m.stars) + '|' + m.name)


def print_categories(categories, server_type, maps_set):
    for c in categories:
        maps = Map.objects.filter(server_type=server_type, categories=c).order_by(Lower('name'))
        # TODO: at some point this should not be neccessary anymore
        if maps and not maps_set.issuperset(maps):
            print()
            print('─── ' + c.name.upper() + ' ───')

            for m in maps:
                if m not in maps_set:
                    maps_set.add(m)
                    print_map(m)


def print_mapfile(server_type):
    print('$add_vote "Make sure no one is racing before voting!" "info"')
    print('$add_vote "Random {} Map" "random_map"'.format(server_type))
    print('$add_vote "Random {} Map Unfinished by Vote Caller" "random_unfinished_map"'.format(server_type))

    if server_type != 'DDmaX':
        print()
        print('─── NEW MAPS ───')

        maps = Map.objects.filter(server_type=server_type).order_by('-timestamp')[:7]

        maps_set = set(maps)

        for m in maps:
            print_map(m)
    else:
        maps_set = set()

    categories = MapCategory.objects.filter(order__lte=100).order_by('order', 'name')
    print_categories(categories, server_type, maps_set)

    print()
    print('─── OTHER MAPS ───')

    for m in Map.objects.filter(server_type=server_type, categories=None).order_by(Lower('name')):
        if m not in maps_set:
            print_map(m)

    categories = MapCategory.objects.filter(order__gt=100).order_by('order', 'name')
    print_categories(categories, server_type, maps_set)


def release_maps_thread(on_finished=None):
    '''Run the release process.'''
    objects = MapRelease.objects.filter(state=PROCESS.PENDING.value)
    objects.update(timestamp=timezone.now())
    logobj = ReleaseLog()
    try:
        maps = []
        # Create Map entries for the Maps table
        for mr in objects:
            m = mr.to_Map()
            m.save()
            maps.append(m)

        q = current_release_log().queue
        p = subprocess.Popen(
            ['map_release'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        p.stdin.write(bytes(json.dumps(
            {
                m.name:
                    {
                        'map': m.mapfile.path,
                        'image': m.img.path,
                        'mapper': m.mapper,
                        'server_type': m.server_type.name
                    } for m in objects
            }
        ), encoding='utf-8'))
        p.stdin.close()
        for line in iter(p.stdout.readline, b''):
            q.put(line.decode('utf-8'))
        p.stdout.close()
        returncode = p.wait()
        if returncode != 0:
            raise RuntimeError('Subprocess terminated with errors.')

        objects.update(state=PROCESS.DONE.value)
        logobj.log = str(current_release_log())
        logobj.state = PROCESS.DONE.value

        try:
            p = subprocess.Popen(
                ['map_release_done'],
                stdin=subprocess.PIPE,
            )
            p.stdin.write(bytes(json.dumps(
                {
                    m.name:
                        {
                            'mapper': m.mapper,
                            'stars': m.stars,
                            'points': m.points,
                            'server_type': m.server_type.name
                        } for m in maps
                }
            ), encoding='utf-8'))
            p.stdin.close()
            returncode = p.wait()
            if returncode != 0:
                logger.info('map_release_done terminated with errors.')
        except FileNotFoundError:
            # this is optional, so no error if there is no hook
            pass
        except Exception:
            logger.exception('An Exception occured while executing map_release_done.')
    except Exception as e:
        # revert Mapreleases
        for m in maps:
            try:
                m.delete()
            except Exception:
                pass
        objects.update(state=PROCESS.FAILED.value)
        logobj.log = str(current_release_log()) + str(e)
        logobj.state = PROCESS.FAILED.value
    finally:
        logobj.save()
        del LOGS['release']
        if on_finished:
            on_finished(logobj.state)
        logger.info('Maprelease done')


def release_maps(mapreleases, on_finished=None):
    if mapreleases and not MapRelease.objects.filter(state=PROCESS.PENDING.value):
        logger.info('Starting maprelease')
        LOGS['release'] = Log()
        mapreleases.update(state=PROCESS.PENDING.value)
        t = Thread(target=release_maps_thread, args=(on_finished,))
        t.daemon = True
        t.start()
    elif on_finished:
        logger.warning('Maprelease failed (%s)', mapreleases)
        on_finished(PROCESS.FAILED.value)


def fix_maps_thread():
    '''Run the mapfix process.'''
    objects = MapFix.objects.filter(state=PROCESS.PENDING.value)
    objects.update(timestamp=timezone.now())
    logobj = FixLog()
    try:
        q = current_fix_log().queue
        p = subprocess.Popen(
            ['map_fix'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        p.stdin.write(bytes('\n'.join(m.mapfile.path for m in objects), encoding='utf-8'))
        p.stdin.close()
        for line in iter(p.stdout.readline, b''):
            q.put(line.decode('utf-8'))
        p.stdout.close()
        returncode = p.wait()
        if returncode != 0:
            raise RuntimeError('Subprocess terminated with errors.')

        objects.update(state=PROCESS.DONE.value)
        logobj.log = str(current_fix_log())
        logobj.state = PROCESS.DONE.value
    except Exception as e:
        objects.update(state=PROCESS.FAILED.value)
        logobj.log = str(current_fix_log()) + str(e)
        logobj.state = PROCESS.FAILED.value
    finally:
        logobj.save()
        del LOGS['fix']
        logger.info('Mapfix done')


def fix_maps(mapfixes):
    if mapfixes and not MapFix.objects.filter(state=PROCESS.PENDING.value):
        logger.info('Starting mapfix')
        LOGS['fix'] = Log()
        mapfixes.update(state=PROCESS.PENDING.value)
        t = Thread(target=fix_maps_thread)
        t.daemon = True
        t.start()


@log_exception(
    lambda e: logger.exception('An Exception occured in handle_scheduled_releases'),
    Exception,
    retry_seconds=30
)
def handle_scheduled_releases():
    while True:
        sleep_time = 300
        try:
            release = ScheduledMapRelease.objects.filter(
                state=PROCESS.NOT_STARTED.value
            ).latest('release_date')
        except ObjectDoesNotExist:
            time.sleep(sleep_time)
            continue

        pending = False

        # time is up...
        if release.release_date < timezone.now():
            pending = True

            # ...and no release pending ?
            if not MapRelease.objects.filter(state=PROCESS.PENDING.value):
                release.state = PROCESS.PENDING.value
                release.save()
                pk = release.pk

                def on_finished(state):
                    release = ScheduledMapRelease.objects.get(pk=pk)
                    release.state = state
                    release.save()
                    if state == PROCESS.DONE.value:
                        if release.broadcast:
                            try:
                                subprocess.Popen(
                                    ['ddnet_broadcast', release.broadcast],
                                    stdout=subprocess.DEVNULL
                                ).wait(timeout=31)
                            except subprocess.TimeoutExpired:
                                logger.warning('Scheduled Release: Broadcast failed.')

                release_maps(
                    release.maps.filter(state=PROCESS.NOT_STARTED.value),
                    on_finished=on_finished
                )
        # try to be precise
        elif not pending and (release.release_date - timezone.now()).total_seconds() < sleep_time:
            sleep_time = (release.release_date - timezone.now()).total_seconds() + 1
            if sleep_time < 0:
                sleep_time = 0

        time.sleep(sleep_time)


@log_exception(
    lambda e: logger.exception('An Exception occured in handle_cleanup'),
    Exception,
    retry_seconds=30
)
def handle_cleanup():
    while True:
        days = 3
        days_ago = timezone.now() - timedelta(days=days)

        # delete everything older than three days except its state is pending or not started
        querysets = [
            MapRelease.objects.filter(
                Q(timestamp__lte=days_ago) &
                ~(Q(state=PROCESS.NOT_STARTED.value) | Q(state=PROCESS.PENDING.value))
            ),
            MapFix.objects.filter(
                Q(timestamp__lte=days_ago) &
                ~(Q(state=PROCESS.NOT_STARTED.value) | Q(state=PROCESS.PENDING.value))
            ),
            ReleaseLog.objects.filter(
                Q(timestamp__lte=days_ago) &
                ~(Q(state=PROCESS.NOT_STARTED.value) | Q(state=PROCESS.PENDING.value))
            ),
            FixLog.objects.filter(
                Q(timestamp__lte=days_ago) &
                ~(Q(state=PROCESS.NOT_STARTED.value) | Q(state=PROCESS.PENDING.value))
            ),
            ScheduledMapRelease.objects.filter(
                Q(release_date__lte=days_ago) &
                ~(Q(state=PROCESS.NOT_STARTED.value) | Q(state=PROCESS.PENDING.value))
            ),
        ]

        # Make sure delete is called for every object so we do not leave out any custom deletes
        for q in querysets:
            for o in q:
                o.delete()

        # every six hours should be more than sufficient
        time.sleep(60*60*6)
