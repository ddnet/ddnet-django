'''URL-definitions for the skindatabase.'''

from django.conf.urls import url

from .views import ReleaseLogView, FixLogView

app_name = 'maps'

urlpatterns = [
    url(r'^api/release/log/$', ReleaseLogView.as_view(), name='release_log'),
    url(r'^api/fix/log/$', FixLogView.as_view(), name='fix_log'),
]
