from django.conf.urls import url

from ddnet_django import admin
from .models import MapRelease, ServerType, Map


admin.site.register(MapRelease)
admin.site.register(ServerType)
admin.site.register(Map)
