'''Tests for the mapfix upload pipeline.'''

import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connections
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Map, MapFix, ServerType


class MapFixPipelineTest(TestCase):
    databases = {'default', 'ddnet_db'}

    @classmethod
    def setUpClass(cls):
        # The Map table lives in the (unmanaged) game database, so the test
        # database does not contain it; create it by hand.
        with connections['ddnet_db'].schema_editor() as editor:
            editor.create_model(Map)

        cls.tmpdir = tempfile.mkdtemp()
        cls.media_override = override_settings(
            MEDIA_ROOT=os.path.join(cls.tmpdir, 'media')
        )
        cls.media_override.enable()

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        st = ServerType.objects.create(name='Novice', offset=0, multiplier=1)
        for name in ('Kobra 4', 'Sunny Side Up', 'Back in Time 3'):
            Map(
                name=name, server_type=st, mapper='x', stars=1, timestamp=timezone.now()
            ).save()
        cls.user = User.objects.create_superuser('admin', 'admin@localhost', 'pw')

    def setUp(self):
        self.client.force_login(self.user)

    def test_search_ranks_closest_mapname_first(self):
        for query, expected in (
            ('kobr 4', 'Kobra 4'),
            ('Sunny_Side_Up', 'Sunny Side Up'),
            ('bck in tme 3', 'Back in Time 3'),
        ):
            response = self.client.get(reverse('admin:map_fix_search'), {'q': query})
            names = [r['name'] for r in response.json()['results']]
            self.assertEqual(names[0], expected)

    def test_upload_pairs_files_with_mapnames(self):
        response = self.client.post(reverse('admin:map_fix_upload'), {
            'mapfiles': [
                SimpleUploadedFile('a.map', b'CONTENT-A'),
                SimpleUploadedFile('b.map', b'CONTENT-B'),
            ],
            'mapnames': ['Kobra 4', 'Sunny Side Up'],
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertIn('redirect', response.json())
        self.assertEqual(MapFix.objects.count(), 2)
        # the n-th mapname belongs to the n-th file
        self.assertEqual(MapFix.objects.get(ddmap='Kobra 4').mapfile.read(), b'CONTENT-A')
        self.assertEqual(
            MapFix.objects.get(ddmap='Sunny Side Up').mapfile.read(), b'CONTENT-B'
        )

    def test_upload_with_unknown_mapname_creates_nothing(self):
        response = self.client.post(reverse('admin:map_fix_upload'), {
            'mapfiles': [
                SimpleUploadedFile('a.map', b'A'),
                SimpleUploadedFile('b.map', b'B'),
            ],
            'mapnames': ['Kobra 4', 'Not A Map'],
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 400)
        self.assertIn('Not A Map', response.json()['errors'][0])
        self.assertEqual(MapFix.objects.count(), 0)

    def test_upload_without_mapnames_matches_filenames(self):
        # without javascript only files are sent; filenames are fuzzy-matched
        response = self.client.post(reverse('admin:map_fix_upload'), {
            'mapfiles': [SimpleUploadedFile('Sunny_Side_Up.map', b'A')],
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(MapFix.objects.get().ddmap_id, 'Sunny Side Up')

    def test_upload_of_unmatchable_filename_is_rejected(self):
        response = self.client.post(reverse('admin:map_fix_upload'), {
            'mapfiles': [SimpleUploadedFile('qqqqqqqq.map', b'A')],
        })

        self.assertContains(response, 'Could not match')
        self.assertEqual(MapFix.objects.count(), 0)

    def test_admin_add_redirects_to_upload_pipeline(self):
        response = self.client.get(reverse('admin:maps_mapfix_add'))
        self.assertRedirects(response, reverse('admin:map_fix_upload'))

    def test_changelist_redirects_to_upload_pipeline(self):
        changelist = reverse('admin:maps_mapfix_changelist')
        response = self.client.get(changelist)
        self.assertRedirects(response, reverse('admin:map_fix_upload'))
        # the plain list stays reachable with a querystring
        response = self.client.get(changelist + '?q=')
        self.assertEqual(response.status_code, 200)

    def test_diff_without_released_mapfile(self):
        with override_settings(MAPS_DIR=None):
            response = self.client.post(reverse('admin:map_fix_diff'), {
                'mapname': 'Kobra 4',
                'mapfile': SimpleUploadedFile('Kobra 4.map', b'A'),
            })

        data = response.json()
        self.assertFalse(data['found'])
        self.assertEqual(MapFix.objects.count(), 0)

    def test_diff_reports_tile_changes(self):
        import twmap

        old = twmap.Map.empty('DDNet06')
        old.groups.new_physics()
        game = old.groups[0].layers.new_game(50, 40)
        tiles = game.tiles
        tiles[5, 5:10, 0] = 1
        game.tiles = tiles

        # released mapfiles may sit in nested directories
        maps_dir = os.path.join(self.tmpdir, 'maps')
        os.makedirs(os.path.join(maps_dir, 'some', 'subdir'), exist_ok=True)
        old.save(os.path.join(maps_dir, 'some', 'subdir', 'Kobra 4.map'))

        tiles[5, 5:7, 0] = 0
        game.tiles = tiles
        fix_bytes = old.to_bytes()

        with override_settings(MAPS_DIR=maps_dir):
            response = self.client.post(reverse('admin:map_fix_diff'), {
                'mapname': 'Kobra 4',
                'mapfile': SimpleUploadedFile('Kobra 4.map', fix_bytes),
            })

            data = response.json()
            self.assertTrue(data['found'])
            self.assertTrue(data['changes'])
            self.assertIn('Game "Game": 2 tiles (−2)', data['lines'])

            # uploading stores the same summary as changelog metadata
            response = self.client.post(reverse('admin:map_fix_upload'), {
                'mapfiles': [SimpleUploadedFile('Kobra 4.map', fix_bytes)],
                'mapnames': ['Kobra 4'],
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertIn('Game "Game": 2 tiles (−2)', MapFix.objects.get().changelog)
