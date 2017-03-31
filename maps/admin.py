from django.contrib.admin import ModelAdmin
from django.http import HttpResponseRedirect
from django.contrib import admin as dj_admin
from django.urls import reverse
from django.conf.urls import url

from ddnet_django import admin
from .models import (
    MapRelease, ServerType, Map, MapCategory, MapFix, ReleaseLog, FixLog, ScheduledMapRelease,
    PROCESS
)
from .views import MapReleaseView, MapFixView


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


def release_action(modeladmin, request, queryset):
    selected = request.POST.getlist(dj_admin.ACTION_CHECKBOX_NAME)
    return HttpResponseRedirect(reverse('admin:map_release') + '?ids={}'.format(','.join(selected)))


release_action.short_description = 'Release map(s)'


class MapReleaseAdmin(ModelAdmin):
    list_display = (
        'name',
        'state',
        'timestamp'
    )
    list_filter = ('state',)
    readonly_fields = (
        'timestamp',
    )

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.state == PROCESS.PENDING.value:
            return super().get_fields(request)
        return super().get_readonly_fields(request)

    actions = [release_action]

    def get_urls(self):
        return super().get_urls() + [
            url(r'^release', MapReleaseView.as_view(), name='map_release'),
        ]


def fix_action(modeladmin, request, queryset):
    selected = request.POST.getlist(dj_admin.ACTION_CHECKBOX_NAME)
    return HttpResponseRedirect(reverse('admin:map_fix') + '?ids={}'.format(','.join(selected)))


fix_action.short_description = 'Fix map(s)'

class MapFixAdmin(ModelAdmin):
    raw_id_fields = ("ddmap",)
    list_display = (
        'name',
        'state',
        'timestamp'
    )
    readonly_fields = (
        'timestamp',
    )
    actions = [fix_action]

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.state == PROCESS.PENDING.value:
            return super().get_fields(request)
        return super().get_readonly_fields(request)

    def get_urls(self):
        return super().get_urls() + [
            url(r'^fix', MapFixView.as_view(), name='map_fix'),
        ]


class ScheduledMapReleaseAdmin(ModelAdmin):
    list_display = (
        'release_date',
        'state'
    )

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.state == PROCESS.PENDING.value:
            return super().get_fields(request)
        return super().get_readonly_fields(request)


class ReleaseLogAdmin(ModelAdmin):
    list_display = (
        'timestamp',
        'state'
    )

class FixLogAdmin(ModelAdmin):
    list_display = (
        'timestamp',
        'state'
    )


admin.site.register(MapRelease, MapReleaseAdmin)
admin.site.register(MapFix, MapFixAdmin)
admin.site.register(ServerType)
admin.site.register(MapCategory, MapCategoryAdmin)
admin.site.register(Map, MapAdmin)
admin.site.register(ReleaseLog, ReleaseLogAdmin)
admin.site.register(FixLog, FixLogAdmin)
admin.site.register(ScheduledMapRelease, ScheduledMapReleaseAdmin)
