import queue
import subprocess
from threading import Thread
from django.views.generic.base import TemplateView, View
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render
from django.http import HttpResponse, Http404

from ddnet.utils import Log

from .models import Broadcast

BLOG = None
BROADCASTING = 0

class BroadcastView(PermissionRequiredMixin, TemplateView):
    template_name = 'admin/servers/broadcast/broadcast.html'
    permission_required = 'servers.can_broadcast'
    admin = None
    model = Broadcast

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'opts': self.model._meta, # NOQA
            'app_label': self.model._meta.app_label, # NOQA
        })
        ctx.update(self.admin.each_context(self.request))
        return ctx

    def post(self, request, *args, **kwargs):
        global BROADCASTING
        ctx = self.get_context_data()
        bc = request.POST.get('broadcast', None)

        if bc:
            ctx['broadcasting'] = True
            BROADCASTING += 1
            t = Thread(target=self.target, args=(bc,))
            t.daemon = True
            t.start()
        return render(request, self.get_template_names(), ctx)

    def target(self, bc):
        '''Run the broadcast process.'''
        global BLOG, BROADCASTING
        BLOG = Log()
        q = BLOG.queue

        try:
            p = subprocess.Popen(
                ['ddnet_broadcast', bc],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            for line in iter(p.stdout.readline, b''):
                q.put(line.decode('utf-8'))
            p.stdout.close()
            returncode = p.wait()
            if returncode != 0:
                raise RuntimeError('Subprocess terminated with errors.')

        except Exception as e:
            q.put(str(e))
        finally:
            BROADCASTING -= 1


class BroadcastLogView(PermissionRequiredMixin, View):
    permission_required = 'maps.can_broadcast'

    def get(self, request, *args, **kwargs):
        '''Return plaintext broadcastlog.'''
        global BLOG, BROADCASTING

        b = request.GET.get('broadcasting', None)
        if b is not None:
            if BROADCASTING != 0:
                return HttpResponse(str(BROADCASTING))
            else:
                raise Http404
        return HttpResponse(str(BLOG) if BLOG is not None else '')
