from django.contrib import admin

from .models import MapRelease, ServerType, Map


admin.site.register(MapRelease)
admin.site.register(ServerType)
admin.site.register(Map)
