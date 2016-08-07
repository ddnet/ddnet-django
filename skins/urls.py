'''URL-definitions for the skindatabase.'''

from django.conf.urls import url

from skins.views import SkinListView
from . import views

app_name = 'skins'

urlpatterns = [
    # url(r'^$', HomeView.customize(template_name='skins/index.html').as_view(), name='index'),

    url(r'^$', SkinListView.as_view(), name='skin_list'),
    url(r'^add-to-download', views.add_to_download),
    url(r'^remove-from-download$', views.remove_from_download),
    url(r'^clear-download-list$', views.clear_download_list),
    url(r'^download-selected$', views.download_selected)
]
