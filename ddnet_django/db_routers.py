'''Definitions for Databaserouters that determine which database belongs to a specific app.'''

APP_DATABASES = {
    'skins': 'skins_db',
    'maps': 'ddnet_db',
}


class DefaultRouter:
    '''
    Each App can have its own database, APP_DATABASES determines which.

    If no database to use is specified the default-database will be used. This is the case for all
    django-internal models required for authentication and administration etc. .
    '''

    def db_for_read(self, model, **hints):
        '''
        Return database to read from depending on a given model.
        '''
        try:
            return APP_DATABASES[model._meta.app_label]
        except KeyError:
            return None

    def db_for_write(self, model, **hints):
        '''
        Return database to write to depending on a given model.
        '''
        try:
            return APP_DATABASES[model._meta.app_label]
        except KeyError:
            return None

    def allow_relation(self, obj1, obj2, **hints):
        '''
        Return whether a relation between two objects is allowed.

        Only has an opinion if at least one of the objects belongs to an app
        with its own database; everything else (e.g. django-internal relations
        like Permission <-> ContentType) is left to the default behaviour.
        '''
        db1 = APP_DATABASES.get(obj1._meta.app_label)
        db2 = APP_DATABASES.get(obj2._meta.app_label)
        if db1 or db2:
            return db1 == db2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        '''
        Return whether migrations are allowed depending on a given database and appname.
        '''
        try:
            return APP_DATABASES[app_label] == db
        except KeyError:
            return None
