import datetime

from django.core.files.base import ContentFile
from django.http import HttpResponse

from ddnet_base.session_attributes import SessionAttribute, SessionAttributeUtil
from ddnet_base.views import DDListView
from .models import Skin


# Main view class
class SkinListView(DDListView):
    model = Skin

    def get_context_data(self, **kwargs):
        context = super(SkinListView, self).get_context_data(**kwargs)
        context['selected_skins_to_download'] = SessionAttributeUtil.get(self.request, SessionAttribute.SELECTED_SKINS, [])
        return context


# Additional view methods
def add_to_download(request):
    # get the currently selected skins as set, which unfortunately is not serializable
    selected_skins = SessionAttributeUtil.get(request, SessionAttribute.SELECTED_SKINS, [])
    selected_skins_set = set(selected_skins)

    skin_name = __get_skin_name(request)
    selected_skins_set.add(skin_name)

    selected_skins = list(selected_skins_set)
    SessionAttributeUtil.set(request, SessionAttribute.SELECTED_SKINS, selected_skins)

    # return current selection count - we do not need to send the whole list
    return HttpResponse(len(selected_skins))


def remove_from_download(request):
    selected_skins = SessionAttributeUtil.get(request, SessionAttribute.SELECTED_SKINS, [])

    skin_name = __get_skin_name(request)
    try:
        selected_skins.remove(skin_name)
    except ValueError:
        pass

    SessionAttributeUtil.set(request, SessionAttribute.SELECTED_SKINS, selected_skins)

    # return current selection count - we do not need to send the whole list
    return HttpResponse(len(selected_skins))


def clear_download_list(request):
    selected_skins = SessionAttributeUtil.get(request, SessionAttribute.SELECTED_SKINS, [])
    selected_skins.clear()

    SessionAttributeUtil.set(request, SessionAttribute.SELECTED_SKINS, selected_skins)

    return HttpResponse()


def __get_skin_name(request):
    return request.POST.get('skinName')
