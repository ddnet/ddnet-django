from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions

from django.utils.deconstruct import deconstructible


@deconstructible
class image_validator:

    def __init__(self, w, h):
        self.width = w
        self.height = h

    def __call__(self, img):
        w, h = get_image_dimensions(img)

        if w != self.width:
            raise ValidationError('Image must be {} px wide, not {} px.'.format(self.width, w))

        if h != self.height:
            raise ValidationError('Image must be {} px high, not {} px.'.format(self.height, h))
