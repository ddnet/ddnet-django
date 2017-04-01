'''Views for the maps app.'''

from django.views.generic.detail import View
from django.views.generic.detail import TemplateResponseMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse, Http404
from django.shortcuts import redirect, render
from django.core.exceptions import ObjectDoesNotExist

from .models import MapRelease, MapFix, ReleaseLog, FixLog, PROCESS
from .utils import release_maps, fix_maps, current_fix_log, current_release_log


class ProcessListView(PermissionRequiredMixin, TemplateResponseMixin, View):
    '''Class to do some external processing on some Objects.'''

    admin = None

    def get_current_log(self):
        '''Current log.'''
        raise NotImplementedError()

    def run(self, objects):
        '''Method that will invoke the process.'''
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
            log = self.get_last_log()
            ctx['log'] = log and log.log or ''
            if log is not None:
                ctx['process_failed'] = log.state == PROCESS.FAILED.value
        else:
            ctx['log'] = self.get_current_log()
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        '''Trigger the external process if possible.'''
        objects = self.get_objects(self.get_ids(request.POST.get('ids', '')))
        self.run(objects)

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

    def get_current_log(self):
        '''ReleaseLog.'''
        return current_release_log() or ''

    def get_last_log(self):
        '''Get latest releaselog.'''
        try:
            return ReleaseLog.objects.latest('timestamp')
        except ObjectDoesNotExist:
            return None

    def run(self, objects):
        '''Run the release process.'''
        release_maps(objects)


class ReleaseLogView(PermissionRequiredMixin, View):
    '''View for release log.'''

    permission_required = 'maps.can_release_map'

    def get(self, request, *args, **kwargs):
        '''Return plaintext releaselog if it exists otherwise 404.'''

        if current_release_log() is not None:
            return HttpResponse(str(current_release_log()))
        else:
            raise Http404


class MapFixView(ProcessListView):
    '''View for Mapfixes.'''

    model = MapFix
    template_name = 'admin/maps/mapfix/fix_form.html'
    admin = None
    permission_required = 'maps.can_fix_map'

    def get_pending(self):
        '''Return iterable of pending mapfixes.'''
        return self.model.objects.filter(state=PROCESS.PENDING.value)

    def get_current_log(self):
        '''FixLog.'''
        return current_fix_log() or ''

    def get_last_log(self):
        '''Return latest Fixlog.'''
        try:
            return FixLog.objects.latest('timestamp')
        except ObjectDoesNotExist:
            return None

    def run(self, objects):
        '''Run the fix process.'''
        fix_maps(objects)


class FixLogView(PermissionRequiredMixin, View):
    '''View for fixlog.'''

    permission_required = 'maps.can_fix_map'

    def get(self, request, *args, **kwargs):
        '''Return plaintext fixlog if it exists otherwise 404.'''

        if current_fix_log() is not None:
            return HttpResponse(str(current_fix_log()))
        else:
            raise Http404
