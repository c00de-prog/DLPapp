import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import app_dir, validate_url, qualities, download_command, probe_command, progress


class CoreTests(unittest.TestCase):
    def test_url(self):
        self.assertEqual(validate_url(' https://example.com/watch?v=x '), 'https://example.com/watch?v=x')
        for value in ('file:///tmp/video', '-f best', 'example.com', 'https://user:pass@site.test'):
            with self.assertRaises(ValueError):
                validate_url(value)

    def test_real_heights_only(self):
        info = {'formats': [{'height': 1080, 'vcodec': 'avc1'}, {'height': 1080, 'vcodec': 'vp9'},
                            {'height': 720, 'vcodec': 'avc1'}, {'height': 480, 'vcodec': 'none'}]}
        self.assertEqual(qualities(info), [1080, 720])
        for value in ({'entries': []}, {'is_live': True}, {'formats': []}):
            with self.assertRaises(ValueError):
                qualities(value)

    def test_frozen_move(self):
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', '/new/disk/DLPapp/DLPapp.exe'):
            self.assertEqual(app_dir(), Path('/new/disk/DLPapp').resolve())

    def test_cli_quality_and_paths(self):
        with tempfile.TemporaryDirectory(prefix='Link Drop ') as temp:
            root = Path(temp)
            tools = root / 'tools'
            tools.mkdir()
            for name in ('yt-dlp', 'ffmpeg', 'ffprobe', 'deno'):
                (tools / (name + ('.exe' if os.name == 'nt' else ''))).touch()
            cmd = download_command(root, 'https://example.com/watch?v=x&list=y', 720, root / 'Downloads')
            self.assertEqual(cmd[cmd.index('-f') + 1], 'bv[height=720]+ba/b[height=720]/bv[height=720]')
            self.assertEqual(cmd[cmd.index('-P') + 1], str(root / 'Downloads'))
            self.assertEqual(cmd[-2], '--')
            self.assertIn('--ignore-config', cmd)
            self.assertIn('--dump-single-json', probe_command(root, 'https://example.com/x'))

    def test_sfx_portability(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundled = root / 'temporary-runtime'
            (bundled / 'tools').mkdir(parents=True)
            for name in ('yt-dlp', 'ffmpeg', 'ffprobe', 'deno'):
                (bundled / 'tools' / (name + ('.exe' if os.name == 'nt' else ''))).touch()
            with patch.object(sys, 'dlpapp_home', str(root / 'moved'), create=True), patch.object(sys, '_MEIPASS', str(bundled), create=True):
                self.assertEqual(app_dir(), (root / 'moved').resolve())
                self.assertTrue(probe_command(app_dir(), 'https://example.com/x')[0].startswith(str(bundled)))

    def test_missing_tool(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'tools/'):
                probe_command(Path(temp), 'https://example.com/x')

    def test_progress(self):
        self.assertEqual(progress('PROGRESS: 42.5%| 2MiB/s | 00:08'), (42.5, '2MiB/s · 00:08'))
        self.assertIsNone(progress('PROGRESS:NA|NA|NA'))
        self.assertIsNone(progress('[download] useful text'))


if __name__ == '__main__':
    unittest.main()
