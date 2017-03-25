from threading import Thread
import subprocess
from queue import Queue
from django.shortcuts import render
from django.views.generic.detail import View
from django.views.generic.detail import SingleObjectMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse, Http404


from .models import MapRelease, MapFix, PROCESS


class Logs:

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

# Releases
RLOGS = Logs()

# Fixes
FLOGS = Logs()


def release_map(m):
    try:
        q = Queue()
        RLOGS[m.pk] = q
        p = subprocess.Popen(
            ['map_release', m.name, m.mapfile.path, m.img.path, m.mapper, m.server_type.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        for line in iter(p.stdout.readline, b''):
            q.put(line.decode('utf-8'))
        p.stdout.close()
        returncode = p.wait()
        m.log = RLOGS[m.pk]
        if returncode == 0:
            m.release_state = PROCESS.DONE.value
        else:
            m.release_state = PROCESS.FAILED.value
    except Exception as e:
        m.release_state = PROCESS.FAILED.value
        m.log = str(e)
    finally:
        del RLOGS[m.pk]
    m.save()


class MapReleaseView(PermissionRequiredMixin, SingleObjectMixin, View):
    model = MapRelease
    template_name = 'admin/maps/maprelease/release_form.html'
    admin = None
    permission_required = 'maps.can_release_map'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.admin.each_context(self.request))
        ctx.update({
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        })
        if self.object.release_state == PROCESS.PENDING.value:
            ctx['log'] = RLOGS[self.object.pk]
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.release_state == PROCESS.NOT_STARTED.value:
            self.object.release_state = PROCESS.PENDING.value
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


def fix_map(m):
    try:
        q = Queue()
        FLOGS[m.pk] = q
        p = subprocess.Popen(
            ['map_fix', m.mapfile.path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        for line in iter(p.stdout.readline, b''):
            q.put(line.decode('utf-8'))
        p.stdout.close()
        returncode = p.wait()
        m.log = FLOGS[m.pk]
        if returncode == 0:
            m.fix_state = PROCESS.DONE.value
        else:
            m.fix_state = PROCESS.FAILED.value
    except Exception as e:
        m.fix_state = PROCESS.FAILED.value
        m.log = str(e)
    finally:
        del FLOGS[m.pk]

    m.save()


class MapFixView(PermissionRequiredMixin, SingleObjectMixin, View):
    model = MapFix
    template_name = 'admin/maps/mapfix/fix_form.html'
    admin = None
    permission_required = 'maps.can_release_map'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.admin.each_context(self.request))
        ctx.update({
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        })
        if self.object.fix_state == PROCESS.PENDING.value:
            ctx['log'] = FLOGS[self.object.pk]
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.fix_state == PROCESS.NOT_STARTED.value:
            self.object.fix_state = PROCESS.PENDING.value
            self.object.save()

            t = Thread(target=fix_map, args=(self.object,))
            t.daemon = True
            t.start()

        return render(request, self.template_name, self.get_context_data())


class FixLogView(PermissionRequiredMixin, View):
    permission_required = 'maps.can_release_map'

    def get(self, request, *args, **kwargs):
        pk = int(kwargs['pk'])
        s = FLOGS[pk]
        if s is not None:
            return HttpResponse(s)
        else:
            raise Http404
