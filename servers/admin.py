from django.conf.urls import url
from django.urls import reverse_lazy
from django.views.generic import RedirectView
from django.contrib.admin import ModelAdmin

from ddnet_django import admin

from .models import Broadcast
from .views import BroadcastView

class BroadcastAdmin(ModelAdmin):
    def get_urls(self):
        info = Broadcast._meta.app_label, Broadcast._meta.model_name
        urlpatterns = [
            url(r'^broadcast', BroadcastView.as_view(), name='broadcast'),
            url(r'^$', RedirectView.as_view(pattern_name='admin:broadcast'), name='%s_%s_changelist' % info),
        ]
        return urlpatterns


admin.site.register(Broadcast, BroadcastAdmin)
