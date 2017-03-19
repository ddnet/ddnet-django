'''Models are registered here to provide access for the admininterface.'''

from ddnet_django import admin
from django.contrib.admin import ModelAdmin


from .models import Skin


class SkinAdmin(ModelAdmin):
    list_display = (
        'name',
        'creator',
        'pack',
        'release_date'
    )

    list_filter = (
        'pack',
        'creator'
    )
    search_fields = (
        'name',
        'creator',
        'pack',
    )


admin.site.register(Skin, SkinAdmin)
