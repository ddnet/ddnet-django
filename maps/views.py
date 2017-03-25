from threading import Thread
import subprocess
from queue import Queue
from django.shortcuts import render
from django.views.generic.detail import View
from django.views.generic.detail import SingleObjectMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse, Http404


from .models import MapRelease, RELEASE


class ReleaseLogs:

    def __init__(self):
        self._logs = {}

    def __setitem__(self, key, value):
        self._logs[key] = [value, '']

    def __getitem__(self, key):
        try:
            q = self._logs[key][0]
            s = ''
            while not q.empty():
                s += q.get_nowait()
            self._logs[key][1] += s
            return self._logs[key][1]
        except KeyError:
            return None

    def __delitem__(self, key):
        self._logs.pop(key)


RLOGS = ReleaseLogs()


def release_map(m):
    q = Queue()
    RLOGS[m.pk] = q
    p = subprocess.Popen(['map_release'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(p.stdout.readline, b''):
        q.put(line.decode('utf-8'))
    p.stdout.close()
    returncode = p.wait()
    m.log = RLOGS[m.pk]
    del RLOGS[m.pk]
    if returncode == 0:
        m.release_state = RELEASE.DONE.value
    else:
        m.release_state = RELEASE.FAILED.value
    m.save()


class MapReleaseView(PermissionRequiredMixin, SingleObjectMixin, View):
    model = MapRelease
    template_name = 'admin/maps/maprelease/release_form.html'
    each_context = None
    permission_required = 'maps.can_release_map'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.each_context(self.request))
        if self.object.release_state == RELEASE.PENDING.value:
            ctx['log'] = RLOGS[self.object.pk]
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.release_state == RELEASE.NOT_STARTED.value:
            self.object.release_state = RELEASE.PENDING.value
            self.object.save()

            t = Thread(target=release_map, args=(self.object,))
            t.daemon = True
            t.start()

        return render(request, self.template_name, self.get_context_data())


class ReleaseLogView(PermissionRequiredMixin, View):
    permission_required = 'maps.can_release_map'

    def get(self, request, *args, **kwargs):
        pk = int(kwargs['pk'])
        s = RLOGS[pk]
        if s is not None:
            return HttpResponse(s)
        else:
            raise Http404
