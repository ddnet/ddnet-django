from django.shortcuts import render
from django.views.generic.detail import DetailView

from .models import MapRelease, RELEASE


class MapReleaseView(DetailView):
    model = MapRelease
    template_name = 'admin/maps/maprelease/release_form.html'
    each_context = lambda: print('called')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.each_context(self.request))
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.release_state == RELEASE.NOT_STARTED.value:
            self.object.release_state = RELEASE.PENDING.value
            self.object.save()

            print('TODO: Start the actual release right here !')

        return render(request, self.template_name, self.get_context_data())
