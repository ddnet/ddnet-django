'''URL-definitions for the skindatabase.'''

from django.conf.urls import url

from .views import ReleaseLogView

app_name = 'maps'

urlpatterns = [
    url(r'^api/log/(?P<pk>[0-9]+)$', ReleaseLogView.as_view(), name='release_log'),
]
