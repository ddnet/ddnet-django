from django.contrib import admin

from mapreleases.models import MapRelease


@admin.register(MapRelease)
class MapReleaseAdmin(admin.ModelAdmin):
    readonly_fields = ('tml',)
