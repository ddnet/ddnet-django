'''Views for the maps app.'''

import difflib
import logging
import os

from django.conf import settings
from django.views.generic.detail import View
from django.views.generic.detail import TemplateResponseMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import formats, timezone
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

from .models import Map, MapRelease, MapFix, ReleaseLog, FixLog, PROCESS
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


def ranked_maps(query, limit=10):
    '''Return mapnames with a similarity score, ranked by closeness to the query.'''
    query = query.strip().lower().replace('_', ' ')
    results = []
    for name in Map.objects.values_list('name', flat=True):
        n = name.lower()
        score = difflib.SequenceMatcher(None, query, n).ratio()
        if n == query:
            score += 2
        elif n.startswith(query):
            score += 1
        elif query in n:
            score += .5
        results.append((score, name))
    results.sort(key=lambda t: (-t[0], t[1]))
    return [{'name': n, 'score': round(s, 3)} for s, n in results[:limit]]


class MapFixMapSearchView(PermissionRequiredMixin, View):
    '''Fuzzy mapname search used by the mapfix upload page.'''

    permission_required = 'maps.can_fix_map'

    def get(self, request, *args, **kwargs):
        '''Return a ranked json list of mapnames matching the q parameter.'''
        query = request.GET.get('q', '').strip()
        return JsonResponse({'results': ranked_maps(query) if query else []})


FIX_STATES = {
    PROCESS.NOT_STARTED.value: ('queued', 'Queued'),
    PROCESS.PENDING.value: ('running', 'In progress'),
    PROCESS.DONE.value: ('done', 'Done'),
    PROCESS.FAILED.value: ('failed', 'Failed'),
}


def pipeline_state():
    '''Current state of the fix pipeline as plain data.

    Running and queued fixes come first, followed by the most recent finished
    ones (which the cleanup daemon prunes after a few days).
    '''
    def row(f):
        state, status = FIX_STATES[f.state]
        return {
            'id': f.pk,
            'name': f.name,
            'state': state,
            'status': status,
            'when': formats.date_format(
                timezone.localtime(f.timestamp), 'DATETIME_FORMAT'
            ),
            'log_id': f.log_id,
            'changelog': f.changelog,
        }

    running = list(MapFix.objects.filter(
        state=PROCESS.PENDING.value
    ).order_by('-timestamp'))
    queued = list(MapFix.objects.filter(
        state=PROCESS.NOT_STARTED.value
    ).order_by('-timestamp'))
    finished = list(MapFix.objects.filter(
        state__in=(PROCESS.DONE.value, PROCESS.FAILED.value)
    ).order_by('-timestamp')[:20])

    return {
        'rows': [row(f) for f in running + queued + finished],
        'running': bool(running),
        'queued_ids': ','.join(str(f.pk) for f in queued),
        'live_log': current_fix_log() or '',
    }


class MapFixStatusView(PermissionRequiredMixin, View):
    '''Pipeline state for the upload page, as json.

    Without parameters the current state of all fixes is returned; with
    ?log=<id> the text of that fixlog.
    '''

    permission_required = 'maps.can_fix_map'

    def get(self, request, *args, **kwargs):
        log_id = request.GET.get('log')
        if log_id:
            try:
                return JsonResponse({'log': FixLog.objects.get(pk=int(log_id)).log})
            except (ValueError, FixLog.DoesNotExist):
                return JsonResponse({'error': 'Unknown log.'}, status=404)
        return JsonResponse(pipeline_state())


def find_released_mapfile(name):
    '''Recursively search settings.MAPS_DIR for the released "<name>.map".

    How maps are laid out on the server is not fixed (they may sit in nested
    directories), so the whole tree is walked; if several files match, the
    most recently modified one wins. Returns a path or None.
    '''
    maps_dir = getattr(settings, 'MAPS_DIR', None)
    if not maps_dir or not os.path.isdir(maps_dir):
        return None

    filename = name + '.map'
    best = None
    best_mtime = None
    for root, _dirs, files in os.walk(maps_dir):
        if filename in files:
            path = os.path.join(root, filename)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if best is None or mtime > best_mtime:
                best, best_mtime = path, mtime
    return best


def build_changelog(name, data):
    '''Plain-text diff summary of uploaded map data vs the released mapfile.

    Returns an empty string when diffing is unavailable or fails; the
    changelog is best-effort metadata and never blocks an upload.
    '''
    old_path = find_released_mapfile(name)
    if old_path is None:
        return ''
    try:
        from .mapdiff import MapDiff
    except ImportError:
        return ''
    try:
        with open(old_path, 'rb') as fp:
            result = MapDiff.diff_bytes(fp.read(), data)
    except Exception:
        logger.exception('Building the changelog for "%s" failed.', name)
        return ''
    if result.error:
        return ''
    return '\n'.join(result.summary_lines())


class MapFixDiffView(PermissionRequiredMixin, View):
    '''Diff an uploaded mapfix against the currently released mapfile.

    Takes a multipart POST with "mapfile" and "mapname" and returns a json
    plain-text summary of the structural changes.
    '''

    permission_required = 'maps.can_fix_map'

    def post(self, request, *args, **kwargs):
        f = request.FILES.get('mapfile')
        name = request.POST.get('mapname', '').strip()
        if f is None or not name:
            return JsonResponse({'error': 'mapfile and mapname are required.'}, status=400)
        if not Map.objects.filter(name=name).exists():
            return JsonResponse({'error': 'No map named "{}" exists.'.format(name)}, status=400)

        old_path = find_released_mapfile(name)
        if old_path is None:
            return JsonResponse(
                {'found': False, 'lines': ['No released version found to compare against.']}
            )

        try:
            from .mapdiff import MapDiff
        except ImportError:
            return JsonResponse(
                {'found': False, 'lines': ['Map diffing is unavailable (twmap not installed).']}
            )

        try:
            with open(old_path, 'rb') as fp:
                old_bytes = fp.read()
            result = MapDiff.diff_bytes(old_bytes, f.read())
        except Exception:
            logger.exception('Diffing "%s" against %s failed.', f.name, old_path)
            return JsonResponse({'found': False, 'lines': ['Diff failed.']})

        return JsonResponse({
            'found': True,
            'changes': result.has_changes and not result.error,
            'lines': result.summary_lines(),
        })


class MapFixUploadView(PermissionRequiredMixin, TemplateResponseMixin, View):
    '''Bulk upload of mapfixes.

    Each uploaded file is matched to the closest existing mapname; the match
    can be corrected per file, so fixes for several maps can be uploaded in
    one go and the fix process can be started immediately.
    '''

    model = MapFix
    template_name = 'admin/maps/mapfix/upload_form.html'
    admin = None
    permission_required = ('maps.add_mapfix', 'maps.can_fix_map')

    # minimum difflib ratio for a filename to be matched without confirmation
    FUZZY_THRESHOLD = 0.6

    def get_context_data(self):
        '''Return contextdata including the current state of the fix pipeline.'''
        ctx = {
            'opts': self.model._meta, # NOQA
            'app_label': self.model._meta.app_label, # NOQA
            'pipeline': pipeline_state(),
        }
        ctx.update(self.admin.each_context(self.request))

        return ctx

    def find_map(self, name):
        '''Return the Map with the given name or None.'''
        return (
            Map.objects.filter(name=name).first()
            or Map.objects.filter(name__iexact=name).first()
        )

    def match_file(self, filename):
        '''Fuzzy-match a filename to a Map, or None if no close match exists.'''
        name = os.path.splitext(os.path.basename(filename))[0]
        m = self.find_map(name)
        if m is not None:
            return m

        ranked = ranked_maps(name, limit=1)
        if ranked and ranked[0]['score'] >= self.FUZZY_THRESHOLD:
            return Map.objects.filter(name=ranked[0]['name']).first()
        return None

    def is_ajax(self, request):
        return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    def respond_errors(self, request, errors):
        '''Render errors as json for ajax requests, as html otherwise.'''
        if self.is_ajax(request):
            return JsonResponse({'errors': errors}, status=400)
        ctx = self.get_context_data()
        ctx['errors'] = errors
        return render(request, self.template_name, ctx)

    def get(self, request, *args, **kwargs):
        '''Render the upload form.'''
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        '''Create a MapFix for every uploaded file and optionally start fixing.

        The upload page sends a mapname for each file (chosen or confirmed by
        the user); without javascript only files are sent and each filename is
        fuzzy-matched to a map.
        '''
        files = request.FILES.getlist('mapfiles')
        names = request.POST.getlist('mapnames')

        errors = []
        if not files:
            errors.append('Please select at least one mapfile.')
        if names and len(names) != len(files):
            errors.append(
                'Got {} mapnames for {} files.'.format(len(names), len(files))
            )
            names = []

        matches = []
        for i, f in enumerate(files):
            if names:
                m = self.find_map(names[i].strip())
                if m is None:
                    errors.append(
                        'No map named "{}" exists (file "{}").'.format(names[i], f.name)
                    )
            else:
                m = self.match_file(f.name)
                if m is None:
                    errors.append(
                        'Could not match "{}" to any existing map.'.format(f.name)
                    )
            if m is not None:
                matches.append((m, f))

        if errors:
            return self.respond_errors(request, errors)

        with transaction.atomic():
            fixes = []
            for m, f in matches:
                changelog = build_changelog(m.name, f.read())
                f.seek(0)
                fixes.append(
                    MapFix.objects.create(ddmap=m, mapfile=f, changelog=changelog)
                )

        started = False
        if request.POST.get('start'):
            # fix_maps silently queues when another fix is already running
            already_running = MapFix.objects.filter(state=PROCESS.PENDING.value).exists()
            fix_maps(MapFix.objects.filter(pk__in=[o.pk for o in fixes]))
            started = not already_running
            target = reverse('admin:map_fix')
        else:
            target = reverse('admin:map_fix') + '?ids=' + ','.join(
                str(o.pk) for o in fixes
            )

        if self.is_ajax(request):
            return JsonResponse({'redirect': target, 'started': started})
        return redirect(target)


class FixLogView(PermissionRequiredMixin, View):
    '''View for fixlog.'''

    permission_required = 'maps.can_fix_map'

    def get(self, request, *args, **kwargs):
        '''Return plaintext fixlog if it exists otherwise 404.'''

        if current_fix_log() is not None:
            return HttpResponse(str(current_fix_log()))
        else:
            raise Http404
