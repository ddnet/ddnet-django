import json
import subprocess
from threading import Thread

from django.utils import timezone
from django.db.models.functions import Lower

from ddnet_base.utils import Log

from .models import Map, MapCategory, MapRelease, ReleaseLog, MapFix, FixLog, PROCESS


# Global Logs
# For Releases:
RLOG = None
# For Fixes:
FLOG = None

def current_release_log():
    return RLOG

def current_fix_log():
    return FLOG


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


def release_maps_thread():
    global RLOG
    '''Run the release process.'''
    objects = MapRelease.objects.filter(state=PROCESS.PENDING.value)
    objects.update(release_date=timezone.now())
    logobj = ReleaseLog()
    try:
        maps = []
        # Create Map entries for the Maps table
        for mr in objects:
            m = mr.to_Map()
            m.save()
            maps.append(m)

        q = RLOG.queue
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
        logobj.log = str(RLOG)
        logobj.state = PROCESS.DONE.value
    except Exception as e:
        # revert Mapreleases
        for m in maps:
            try:
                m.delete()
            except Exception:
                pass
        objects.update(state=PROCESS.FAILED.value)
        logobj.log = str(RLOG) + str(e)
        logobj.state = PROCESS.FAILED.value
    finally:
        logobj.save()
        RLOG = None


def release_maps(mapreleases):
    global RLOG
    if mapreleases and not MapRelease.objects.filter(state=PROCESS.PENDING.value):
        RLOG = Log()
        mapreleases.update(state=PROCESS.PENDING.value)
        t = Thread(target=release_maps_thread)
        t.daemon = True
        t.start()


def fix_maps_thread():
    global FLOG
    '''Run the mapfix process.'''
    objects = MapFix.objects.filter(state=PROCESS.PENDING.value)
    objects.update(timestamp=timezone.now())
    logobj = FixLog()
    try:
        q = FLOG.queue
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
        logobj.log = str(FLOG)
        logobj.state = PROCESS.DONE.value
    except Exception as e:
        objects.update(state=PROCESS.FAILED.value)
        logobj.log = str(FLOG) + str(e)
        logobj.state = PROCESS.FAILED.value
    finally:
        logobj.save()
        FLOG = None


def fix_maps(mapfixes):
    global FLOG
    if mapfixes and not MapFix.objects.filter(state=PROCESS.PENDING.value):
        FLOG = Log()
        mapfixes.update(state=PROCESS.PENDING.value)
        t = Thread(target=fix_maps_thread)
        t.daemon = True
        t.start()
