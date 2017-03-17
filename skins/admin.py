'''Models are registered here to provide access for the admininterface.'''

from django.contrib import admin

from .models import Skin


admin.site.register(Skin)
