from enum import Enum, unique

from django.http import HttpRequest


@unique
class SessionAttribute(Enum):
    '''
        Contains a list of a session attributes stored in the session among whole application
        Use the following convention: namespace.attribute_name
    '''
    SELECTED_SKINS = 'skins.selected_skins'


class SessionAttributeUtil:
    '''
    Class created to force using SessionAttribute enum for naming session attributes
    '''

    @staticmethod
    def get(request: HttpRequest, attr_name: SessionAttribute, default_value):
        '''
        Method returns the session attribute given by the attr_name
        or sets a default value if attr_name if the session attribute not exists
        '''
        if attr_name.value not in request.session:
            request.session[attr_name.value] = default_value

        return request.session[attr_name.value]

    @staticmethod
    def set(request: HttpRequest, attr_name: SessionAttribute, attr_value):
        '''
        Method sets the session attribute given by the attr_name and attr_value
        '''
        request.session[attr_name.value] = attr_value

    @staticmethod
    def remove(request: HttpRequest, attr_name: SessionAttribute):
        '''
        Method removes the session attribute given by the attr_name
        '''
        if attr_name.value in request.session:
            del request.session[attr_name.value]
