'''Provide global custom tags for templates.'''

from django import template


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
def url_replace(request, field, value):
    '''
    Change the value of a variable from a GET request.

    If the variable was not specified previously it will be newly created.
    '''
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()
