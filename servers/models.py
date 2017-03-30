from django.db import models


class DummyPermissionModel(models.Model):

    class Meta:
        managed = False

    permissions = (
        ('can_broadcast', 'Can the user do broadcasts on DDNet Servers'),
    )
