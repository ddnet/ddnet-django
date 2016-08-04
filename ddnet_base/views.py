'''Definitions of Views that serve as baseviews containing already most of the required logic.'''

from django.db.models.fields.related import ManyToOneRel
from django.views.generic import ListView

from .factory import ClassFactory


def get_field_names(model):
    '''Return a List of all fieldnames from a given model as strings sorted alphabetically.'''
    return sorted([f.name for f in model._meta.get_fields()  # noqa
                   if not isinstance(f, ManyToOneRel)])


class DDListView(ListView, ClassFactory):
    '''
    Baseclass for Listviews used in this project.

    Features like filtering, ordering etc. should be implemented here.
    '''

    context_object_name = 'items'
    paginate_by = 25
    items_total_count = 0

    def get_template_names(self):
        '''
        Return a list of templates to use for rendering.

        Defaults to: appname + '/list.html'
        '''
        if self.template_name is not None:
            return [self.template_name]
        else:
            return [self.model._meta.app_label + '/list.html']  # noqa
