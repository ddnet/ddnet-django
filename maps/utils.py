from django.db.models.functions import Lower

from .models import Map, MapCategory


def print_map(m):
    if m.mapper and m.mapper != 'Unknown Mapper':
        print(str(m.stars) + '|' + m.name + '|' + m.mapper)
    else:
        print(str(m.stars) + '|' + m.name)


def print_categories(categories, server_type, maps_set):
    for c in categories:
        maps = Map.objects.filter(server_type=server_type, categories=c).order_by(Lower('name'))
        # TODO: at some point this should not be neccessary anymore
        if maps and not maps_set.issuperset(maps):
            print()
            print('─── ' + c.name.upper() + ' ───')

            for m in maps:
                if m not in maps_set:
                    maps_set.add(m)
                    print_map(m)


def print_mapfile(server_type):
    print('$add_vote "Make sure no one is racing before voting!" "info"')
    print('$add_vote "Random {} Map" "random_map"'.format(server_type))
    print('$add_vote "Random {} Map Unfinished by Vote Caller" "random_unfinished_map"'.format(server_type))

    if server_type != 'DDmaX':
        print()
        print('─── NEW MAPS ───')

        maps = Map.objects.filter(server_type=server_type).order_by('-timestamp')[:7]

        maps_set = set(maps)

        for m in maps:
            print_map(m)
    else:
        maps_set = set()

    categories = MapCategory.objects.filter(order__lte=100).order_by('order', 'name')
    print_categories(categories, server_type, maps_set)

    print()
    print('─── OTHER MAPS ───')

    for m in Map.objects.filter(server_type=server_type, categories=None).order_by(Lower('name')):
        if m not in maps_set:
            print_map(m)

    categories = MapCategory.objects.filter(order__gt=100).order_by('order', 'name')
    print_categories(categories, server_type, maps_set)
