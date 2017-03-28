from django.contrib import admin
from django.conf.urls import url

from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin

from maps.views import MapReleaseView, MapFixView


class DDNetAdmin(admin.AdminSite):
    site_header = 'DDNet Administration'

    def get_urls(self):
        urls = super().get_urls()

        extra_urls = [
            url(r'^maps/maprelease/release', MapReleaseView.as_view(), name='map_release'),
            url(r'^maps/mapfix/fix', MapFixView.as_view(), name='map_fix')
        ]

        return urls + extra_urls


site = DDNetAdmin()
MapReleaseView.admin = site
MapFixView.admin = site

site.register(Group, GroupAdmin)
site.register(User, UserAdmin)
