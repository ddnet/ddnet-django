'''Definitions of Views that serve as baseviews containing already most of the required logic.'''

from collections import OrderedDict

from django.db.models.fields.related import ManyToOneRel
from django.views.generic import ListView
from django.db.models import Q, ForeignKey
from django.core.exceptions import ValidationError

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

    def __init__(self, **kwargs):
        # generate order_choices from fields of the model for this object
        self.order_choices = get_field_names(self.model)
        self.GET = dict()
        super().__init__(**kwargs)

    def _get_GET_vars(self, GET):
        '''Retrieve vars from self.request.GET and stored them in a nicer way in self.GET.'''

        self.GET['query'] = GET.get('q', None)
        self.GET['order_by'] = GET.get('o', None)
        self.GET['descending'] = GET.get('desc', None)
        self.GET['filters'] = {k[len('filter_'):]: v
                               for k, v in GET.items() if k.startswith('filter_')}

    def _get_query(self):
        '''Return the Queryobject used for filtering the queryset.'''

        qobj = Q()
        if self.GET['query'] is not None and self.GET['query'] != '' and hasattr(
                self.model,
                'searchfields'
        ):
            for field in self.model.searchfields:
                qobj |= Q(**{field + '__icontains': self.GET['query']})

        if self.GET['filters'] and hasattr(self.model, 'list_filter'):
            for filter_name, filter_value in self.GET['filters'].items():
                if filter_name in self.model.list_filter:
                    try:
                        validated = (
                            self  # noqa
                            .model
                            ._meta
                            .get_field(filter_name)
                            .formfield()
                            .clean(filter_value)
                        )
                        qobj &= Q(**{filter_name + '__exact': validated})
                    except ValidationError:
                        pass

        return qobj

    def get_template_names(self):
        '''Return the names of the templatefiles to use, defaults to [appname + '/list.html'].'''

        if self.template_name is not None:
            return [self.template_name]
        else:
            return [self.model._meta.app_label + '/list.html'] # noqa

    def get_context_data(self, **kwargs):
        '''
        Get contextdata required for rendering the template.

        The following things are provided for templates:

        descending: defines whether the objects should be ordered descending.
        order_by: defines by which modelattribute to order the list.
        query: contains the string to search for.
        '''
        context = super().get_context_data(**kwargs)
        context['order_choices'] = self.order_choices

        if self.GET['query'] is not None:
            context['query'] = self.GET['query']

        if self.GET['order_by'] is not None:
            context['order_by'] = self.GET['order_by']

        if len(self.GET['filters']) > 0:
            context['filters'] = self.GET['filters']

        if hasattr(self.model, 'list_filter'):
            filter_options = OrderedDict()
            for field_name in self.model.list_filter:
                # in case we need to filter a Foreignkey...
                if isinstance(self.model._meta.get_field(field_name), ForeignKey):  # noqa
                    q = (
                        self.model
                        .objects.order_by().
                        distinct(field_name).
                        select_related(field_name)  # query them at once as we will need all of them
                    )
                    filter_options[field_name] = zip(
                        [str(i) for i in list(q.values_list(field_name, flat=True))],
                        # ...get the stringrepresentation of the Foreignkey-object...
                        [str(getattr(i, field_name)) for i in list(q)]
                    )
                else:
                    filter_options[field_name] = [(str(i), str(j)) for i, j in list(
                        self.model
                        .objects
                        .order_by(field_name)
                        # ...otherwise the description will be the
                        # same as the table field
                        .values_list(field_name, field_name)
                        .distinct()
                    )]
            context['filter_options'] = filter_options
        if self.GET['descending'] is not None:
            context['descending'] = self.GET['descending']
        return context

    def get_queryset(self):
        '''
        Return a queryset according to the requested order and query.

        To enable search the underlying Model must define a list of the searchfields as string.

        The search is caseinsensitiv.
        '''

        qobj = self._get_query()

        if qobj is not None:
            qset = self.model.objects.filter(qobj)
        else:
            qset = self.model.objects.all()

        if self.GET['order_by'] in self.order_choices:
            qset = qset.order_by(
                '-' + self.GET['order_by'] if self.GET['descending'] else self.GET['order_by']
            )
        return qset

    def dispatch(self, request, *args, **kwargs):
        '''Delegate request to either get or post method of this class and fill self.GET.'''

        if request.method == 'GET':
            self._get_GET_vars(request.GET)
        return super().dispatch(request, *args, **kwargs)
