from django.apps import apps as django_apps
from django.contrib.auth.management import create_permissions
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'reloads permissions for specified apps, or all apps if no args are specified'

    def add_arguments(self, parser):
        parser.add_argument('apps', nargs='*', type=str)

    def handle(self, *args, **options):
        apps = set()
        if not options['apps']:
            apps = django_apps.get_app_configs()
        else:
            for app in options['apps']:
                apps.add(django_apps.get_app_config(app))

        for app in apps:
            create_permissions(app, 3)
