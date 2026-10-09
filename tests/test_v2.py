import hashlib
import io
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from settings import Settings
from media import format_options, available_heights
from i18n import AppError, STRINGS
from updates import Release, parse_release, download_asset, due, install_script


class SettingsTests(unittest.TestCase):
    def test_migration_preservation_and_foreign_app(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'settings.json'
            path.write_text('{"language":"ru"}')
            s = Settings(path)
            s.update(nickname='Tester', download_parent=temp)
            s.update(last_app_check=42)
            loaded = Settings(path)
            self.assertEqual(loaded.get('nickname'), 'Tester')
            self.assertEqual(loaded.get('language'), 'ru')
            self.assertEqual(json.loads(path.read_text())['app_id'], 'DLPapp')
            path.write_text('{"app_id":"FFClass","nickname":"wrong"}')
            self.assertEqual(Settings(path).get('nickname'), '')

    def test_history_follows_folder_without_moving_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            s = Settings(root / 'settings.json')
            f1 = s.folder(root)
            self.assertEqual(f1.name, 'DDownloads')
            s.record(f1 / 'first.mp4', 'First', f1, 'https://site/video', 'MP4')
            s.update(download_parent=str(root / 'new'))
            f2 = s.folder(root)
            self.assertEqual(s.history(f2), [])
            s.record(f2 / 'second.mp3', 'Second', f2, 'https://site/audio', 'MP3')
            self.assertEqual(s.history(f1)[0]['title'], 'First')
            self.assertEqual(s.history(f2)[0]['format'], 'MP3')
            s.update(download_parent='')
            self.assertEqual(s.history(s.folder(root))[0]['title'], 'First')

    def test_atomic_write_failure_retains_previous_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            s = Settings(Path(temp) / 'settings.json')
            s.update(nickname='old')
            with patch('settings.atomic_json', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    s.update(nickname='new')
            self.assertEqual(s.get('nickname'), 'old')
            self.assertEqual(Settings(s.path).get('nickname'), 'old')

    def test_corrupt_types_and_bounded_history(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'settings.json'
            path.write_text('{"app_id":"DLPapp","history":[4,{}],"nickname":null,"auto_updates":"false","last_app_check":{}}')
            s = Settings(path)
            self.assertEqual(s.get('nickname'), '')
            self.assertEqual(s.get('last_app_check'), 0)
            self.assertEqual(s.history(temp), [])


class FormatTests(unittest.TestCase):
    def test_audio_conversion_and_container_remux(self):
        self.assertEqual(format_options(0, 'MP3')[-3:], ['mp3', '--audio-quality', '0'])
        for fmt in ('MP4', 'MKV', 'WEBM'):
            cmd = format_options(1080, fmt)
            self.assertEqual(cmd[-1], fmt.lower())
            self.assertIn('[height=1080]', cmd[1])
        with self.assertRaises(AppError):
            format_options(720, 'EXE')

    def test_qualities_are_codec_and_container_specific(self):
        info = {'formats': [{'height': 1080, 'vcodec': 'vp9', 'ext': 'webm'}, {'height': 720, 'vcodec': 'avc1'},
                            {'height': 2160, 'vcodec': 'av01', 'ext': 'webm'}, {'height': 1440, 'vcodec': 'none'}]}
        self.assertEqual(available_heights(info, 'MP4'), [2160, 720])
        self.assertEqual(available_heights(info, 'MKV', 'h264'), [720])
        self.assertEqual(available_heights(info, 'WEBM'), [2160, 1080])
        self.assertEqual(available_heights(info, 'MP3'), [])


class Response(io.BytesIO):
    def geturl(self):
        return 'https://release-assets.githubusercontent.com/blob'


class UpdateTests(unittest.TestCase):
    def fixture(self, version='v2.1.0'):
        return {'tag_name': version, 'html_url': 'https://github.com/c00de-prog/DLPapp/releases/tag/' + version,
                'assets': [{'name': 'DLPapp.exe', 'size': 4, 'digest': 'sha256:' + 'a'*64,
                            'browser_download_url': 'https://github.com/c00de-prog/DLPapp/releases/download/' + version + '/DLPapp.exe'}]}

    def test_stable_versions_and_trusted_source(self):
        self.assertIsNone(parse_release(self.fixture('v2.0.0')))
        self.assertIsNotNone(parse_release(self.fixture('v2.10.0')))
        item = self.fixture(); item['assets'][0]['browser_download_url'] = 'https://evil.test/DLPapp.exe'
        with self.assertRaises(AppError):
            parse_release(item)
        item = self.fixture(); item['assets'][0]['digest'] = None
        with self.assertRaises(AppError):
            parse_release(item)
        item = self.fixture(); item['prerelease'] = True
        self.assertIsNone(parse_release(item))

    def test_verified_download_and_partial_cleanup(self):
        payload = b'MZbinary fixture'
        release = Release('2.1.0', '', 'https://github.com/c00de-prog/DLPapp/releases/download/v2.1.0/DLPapp.exe',
                          len(payload), hashlib.sha256(payload).hexdigest(), 'c00de-prog/DLPapp')
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'new.exe'
            with patch('updates.urllib.request.urlopen', return_value=Response(payload)):
                download_asset(release, target)
            self.assertEqual(target.read_bytes(), payload)
            with patch('updates.urllib.request.urlopen', return_value=Response(b'MZbroken')):
                with self.assertRaises(AppError):
                    download_asset(release, target)
            self.assertEqual(target.read_bytes(), payload)
            self.assertFalse(target.with_suffix('.exe.part').exists())
            cancel = threading.Event(); cancel.set()
            with patch('updates.urllib.request.urlopen', return_value=Response(payload)):
                with self.assertRaises(AppError):
                    download_asset(release, target, cancel=cancel)
            self.assertEqual(target.read_bytes(), payload)

    def test_daily_schedule_and_backward_clock(self):
        self.assertFalse(due(100, 101))
        self.assertTrue(due(100, 86500))
        self.assertTrue(due(100, 99))

    def test_installer_escapes_paths_and_preserves_settings(self):
        script = install_script("C:/User's/new.exe", "D:/User's/DLPapp.exe", 123, 'a'*64)
        self.assertIn("User''s", script)
        self.assertIn('Wait-Process -Id 123', script)
        self.assertIn('Get-FileHash', script)
        self.assertNotIn('Recurse', script)
        self.assertNotIn('settings.json', script)

    def test_all_localized_placeholders_match(self):
        import string
        for key in STRINGS['en']:
            fields = lambda value: {f for _, f, _, _ in string.Formatter().parse(value) if f}
            self.assertEqual(fields(STRINGS['en'][key]), fields(STRINGS['ru'][key]), key)

class ExplicitVersionTests(unittest.TestCase):
    def test_diagnostic_uses_explicit_version_without_changing_installed_version(self):
        import updates
        data=UpdateTests().fixture('v2.0.1')
        installed=updates.VERSION
        self.assertIsNotNone(parse_release(data,current_version='2.0.0'))
        self.assertIsNone(parse_release(data,current_version='2.0.1'))
        self.assertEqual(updates.VERSION,installed)
