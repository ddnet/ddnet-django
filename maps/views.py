from django.shortcuts import render
from django.views.generic.detail import View
from django.views.generic.detail import SingleObjectMixin
from django.contrib.auth.mixins import PermissionRequiredMixin

from .models import MapRelease, RELEASE


class MapReleaseView(PermissionRequiredMixin, SingleObjectMixin, View):
    model = MapRelease
    template_name = 'admin/maps/maprelease/release_form.html'
    each_context = None
    permission_required = 'maps.can_release_map'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.each_context(self.request))
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.release_state == RELEASE.NOT_STARTED.value:
            self.object.release_state = RELEASE.PENDING.value
            self.object.save()

            print('TODO: Start the actual release right here !')

        return render(request, self.template_name, self.get_context_data())
