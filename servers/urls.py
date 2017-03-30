'''URL-definitions for Servers.'''

from django.conf.urls import url

from .views import BroadcastView, BroadcastLogView

app_name = 'servers'

urlpatterns = [
    url(r'^api/broadcast/log/$', BroadcastLogView.as_view(), name='broadcast_log'),
]
