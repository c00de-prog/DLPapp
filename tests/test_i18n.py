import ctypes
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from i18n import STRINGS, AppError, detect_language, load_language, save_language


class LanguageTests(unittest.TestCase):
    def test_windows_system_language(self):
        for language_id, expected in ((0x0419, 'ru'), (0x0409, 'en'), (0x0809, 'en'), (0x0407, 'en'), (0x0443, 'en')):
            fake = SimpleNamespace(kernel32=SimpleNamespace(GetUserDefaultUILanguage=lambda: language_id))
            with patch('i18n.os.name', 'nt'), patch.object(ctypes, 'windll', fake, create=True):
                self.assertEqual(detect_language(), expected)

    def test_manual_choice_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'settings.json'
            with patch('i18n.detect_language', return_value='ru'):
                self.assertEqual(load_language(file), 'ru')
                save_language('en', file)
                self.assertEqual(load_language(file), 'en')
                file.write_text('{broken')
                self.assertEqual(load_language(file), 'ru')

    def test_complete_translations_and_errors(self):
        self.assertEqual(set(STRINGS['ru']), set(STRINGS['en']))
        error = AppError('missing_tool', name='ffmpeg.exe')
        self.assertIn('Missing tool', error.localized('en'))
        self.assertIn('Не найден', error.localized('ru'))
