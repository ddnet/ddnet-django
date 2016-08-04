'''Provide global custom tags for templates.'''

from django import template
from itertools import zip_longest

__all__ = (
    'register',
    'paginate_range',
    'url_replace'
)


register = template.Library()


@register.simple_tag
def paginate_range(page_number, page_range, distance=5):
    '''
    Clamp the total range for pagination to something reasonable.

    Return a range surrounding 'page_number' with 'distance' and clamp it if it goes out of
    'page_range'.
    '''
    return range(max(page_number - distance, page_range[0]),
                 min(page_number + distance, page_range[-1]) + 1)


@register.simple_tag
def url_replace(request, *args):
    '''
    Change the value of a field from a GET request.

    If value is left blank or set to None the field will be removed.

    args will be interpreted like this: [field, value, field, value, field ...].
    '''
    dict_ = request.GET.copy()

    for field, value in zip_longest(args[::2], args[1::2], fillvalue=None):
        if value is None:
            try:
                dict_.pop(field)
            except KeyError:
                pass
        else:
            dict_[field] = value
    return dict_.urlencode()
