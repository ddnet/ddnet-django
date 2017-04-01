from django.db import models


# Pretty much a dummy right now
class Broadcast(models.Model):

    class Meta:
        managed = False
        permissions = (
            ('can_broadcast', 'Can the user do broadcasts on DDNet Servers'),
        )
