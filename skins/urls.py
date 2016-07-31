'''URL-definitions for the skindatabase.'''

from django.conf.urls import url

from ddnet_base.views import (
    DDListView,
)

from .models import Skin


app_name = 'skins'

urlpatterns = [
    # url(r'^$', HomeView.customize(template_name='skins/index.html').as_view(), name='index'),

    url(r'^$',
        DDListView.customize(model=Skin).as_view(),
        name='skin_list'),
]
