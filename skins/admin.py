'''Models are registered here to provide access for the admininterface.'''

from ddnet_django import admin


from .models import Skin


admin.site.register(Skin)
