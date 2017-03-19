from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions


def image_validator(width, height):
    def img_val(img):
        w, h = get_image_dimensions(img)

        if w != width:
            raise ValidationError('Image must be {} px wide, not {} px.'.format(width, w))

        if h != height:
            raise ValidationError('Image must be {} px high, not {} px.'.format(height, h))

    return img_val
