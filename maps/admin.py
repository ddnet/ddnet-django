from django.contrib.admin import ModelAdmin

from ddnet_django import admin
from .models import MapRelease, ServerType, Map, MapCategory


class MapAdmin(ModelAdmin):
    list_display = (
        'name',
        'mapper',
        'server_type',
        'stars',
        'timestamp'
    )

    list_filter = (
        'server_type',
        'categories',
    )
    search_fields = (
        'name',
        'mapper',
    )


admin.site.register(MapRelease)
admin.site.register(ServerType)
admin.site.register(MapCategory)
admin.site.register(Map, MapAdmin)
