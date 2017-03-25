from django.contrib.admin import ModelAdmin

from ddnet_django import admin
from .models import MapRelease, ServerType, Map, MapCategory, MapFix, PROCESS


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


class MapCategoryAdmin(ModelAdmin):
    list_display = (
        'name',
        'order'
    )


class MapReleaseAdmin(ModelAdmin):

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.release_state == PROCESS.PENDING.value:
            return super().get_fields(request)
        return super().get_readonly_fields(request)


class MapFixAdmin(ModelAdmin):
    raw_id_fields = ("ddmap",)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.fix_state == PROCESS.PENDING.value:
            return super().get_fields(request)
        return super().get_readonly_fields(request)


admin.site.register(MapRelease, MapReleaseAdmin)
admin.site.register(MapFix, MapFixAdmin)
admin.site.register(ServerType)
admin.site.register(MapCategory, MapCategoryAdmin)
admin.site.register(Map, MapAdmin)
