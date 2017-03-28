'''Views for the maps app.'''

from threading import Thread
import subprocess
import json
from queue import Queue
from django.shortcuts import render
from django.views.generic.detail import View
from django.views.generic.detail import TemplateResponseMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
import datetime


from .models import MapRelease, MapFix, ReleaseLog, FixLog, PROCESS


class Log:
    '''Class to allow non blocking reading from a log being generated.'''

    def __init__(self, q):
        '''Init with a queue where the log is going to be written.'''
        self._queue = q
        self._log = ''

    def __str__(self):
        '''Take everything from the queue and store it within this object and return full log.'''
        s = ''
        while not self._queue.empty():
            s += self._queue.get_nowait()
        self._log += s
        return self._log

    @property
    def queue(self):
        '''The Queue this object is operating on.'''
        return self._queue


# Global Logs
# For Releases:
RLOG = None
# For Fixes:
FLOG = None


class ProcessListView(PermissionRequiredMixin, TemplateResponseMixin, View):
    '''Class to do some external processing on some Objects.'''

    admin = None

    @property
    def log(self):
        '''Log to write to.'''
        raise NotImplementedError()

    @log.setter
    def log(self, val):
        raise NotImplementedError()

    def target(self):
        '''Thread to be executed.'''
        raise NotImplementedError()

    def get_last_log(self):
        '''Return last log created.'''
        raise NotImplementedError()

    def get_ids(self, ids):
        '''Return an id-set from a given string with comma separated ids like '1,4,6,3' .'''
        try:
            ids = set(int(i) for i in ids.split(','))
        except ValueError:
            ids = set()
        return ids

    def update_state(self, objects, state):
        '''Set objects state.'''
        objects.update(state=state)

    def get_pending(self):
        '''Return a list of objects currently being processed.'''
        raise NotImplementedError()

    def get_objects(self, ids):
        '''Return objects with pks the ids set contains.'''
        return self.model.objects.filter(pk__in=ids, state=PROCESS.NOT_STARTED.value)

    def get_context_data(self):
        '''Return essential contextdata.'''
        ctx = {
            'opts': self.model._meta, # NOQA
            'app_label': self.model._meta.app_label, # NOQA
        }
        ctx.update(self.admin.each_context(self.request))

        return ctx

    def get(self, request, *args, **kwargs):
        '''Respond to GET request.'''
        ctx = self.get_context_data()
        pending_objs = self.get_pending()
        objs = None
        ctx['ids'] = request.GET.get('ids', '')
        if not pending_objs:
            objs = self.get_objects(self.get_ids(ctx['ids']))

        ctx['pending_objects'] = pending_objs
        ctx['objects'] = objs
        if not objs and not pending_objs:
            ctx['log'] = self.get_last_log()
        else:
            ctx['log'] = self.log
        print(self.log)
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        '''Trigger the external process if possible.'''
        objects = self.get_objects(self.get_ids(request.POST.get('ids', '')))
        if objects and not self.get_pending():
            self.log = Log(Queue())
            self.update_state(objects, PROCESS.PENDING.value)
            t = Thread(target=self.target)
            t.daemon = True
            t.start()

        return redirect(request.path)


class MapReleaseView(ProcessListView):
    '''View specifically for mapreleases.'''

    model = MapRelease
    template_name = 'admin/maps/maprelease/release_form.html'
    admin = None
    permission_required = 'maps.can_release_map'

    def get_pending(self):
        '''Return iterable of pending mapreleases.'''
        return self.model.objects.filter(state=PROCESS.PENDING.value)

    @property
    def log(self):
        '''ReleaseLog.'''
        return RLOG

    @log.setter
    def log(self, val):
        global RLOG # NOQA - yes there should be only this log
        RLOG = val

    def get_last_log(self):
        '''Get latest releaselog.'''
        obj = ReleaseLog.objects.latest('timestamp')
        return obj and obj.log or ''

    def target(self):
        '''Run the release process.'''
        objects = self.get_pending()
        objects.update(release_date=datetime.datetime.now())
        logobj = ReleaseLog()
        try:
            q = self.log.queue
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

            self.update_state(objects, PROCESS.DONE.value)
            logobj.log = str(self.log)
            logobj.state = PROCESS.DONE.value
        except Exception as e:
            self.update_state(objects, PROCESS.FAILED.value)
            logobj.log = str(self.log) + str(e)
            logobj.state = PROCESS.FAILED.value
        finally:
            self.log = None
            logobj.save()


class ReleaseLogView(PermissionRequiredMixin, View):
    '''View for release log.'''

    permission_required = 'maps.can_release_map'

    def get(self, request, *args, **kwargs):
        '''Return plaintext releaselog if it exists otherwise 404.'''
        if RLOG is not None:
            return HttpResponse(str(RLOG))
        else:
            raise Http404


class MapFixView(ProcessListView):
    '''View for Mapfixes.'''

    model = MapFix
    template_name = 'admin/maps/mapfix/fix_form.html'
    admin = None
    permission_required = 'maps.can_release_map'

    def get_pending(self):
        '''Return iterable of pending mapfixes.'''
        return self.model.objects.filter(state=PROCESS.PENDING.value)

    @property
    def log(self):
        '''Return mapfixlog.'''
        return FLOG

    @log.setter
    def log(self, val):
        global FLOG # NOQA
        FLOG = val

    def get_last_log(self):
        '''Return latest Fixlog.'''
        obj = FixLog.objects.latest('timestamp')
        return obj and obj.log or ''

    def target(self):
        '''Run the mapfix process.'''
        objects = self.get_pending()
        objects.update(timestamp=datetime.datetime.now())
        logobj = FixLog()
        try:
            q = self.log.queue
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

            self.update_state(objects, PROCESS.DONE.value)
            logobj.log = str(self.log)
            logobj.state = PROCESS.DONE.value
        except Exception as e:
            self.update_state(objects, PROCESS.FAILED.value)
            logobj.log = str(self.log) + str(e)
            logobj.state = PROCESS.FAILED.value
        finally:
            self.log = None
            logobj.save()


class FixLogView(PermissionRequiredMixin, View):
    '''View for fixlog.'''

    permission_required = 'maps.can_release_map'

    def get(self, request, *args, **kwargs):
        '''Return plaintext fixlog if it exists otherwise 404.'''
        if FLOG is not None:
            return HttpResponse(str(FLOG))
        else:
            raise Http404
