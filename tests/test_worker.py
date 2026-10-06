"""Real local subprocesses exercise transport without a display or network."""
import json
import queue
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from app import DLPapp


class WorkerTests(unittest.TestCase):
    def worker(self, code, kind='probe', cancelled=False):
        owner = SimpleNamespace(events=queue.Queue(), cancel=threading.Event(), process=None,
                                process_lock=threading.Lock(), _terminate=DLPapp._terminate)
        if cancelled:
            owner.cancel.set()
        DLPapp._worker(owner, [sys.executable, '-c', code], kind, 'https://example.com/video')
        result = []
        while not owner.events.empty():
            result.append(owner.events.get_nowait())
        self.assertIsNone(owner.process)
        return result

    def test_metadata_with_warning(self):
        info = {'title': 'Тест', 'formats': [{'vcodec': 'avc1', 'height': 720}]}
        events = self.worker('print("WARNING: notice"); print(' + repr(json.dumps(info)) + ')')
        self.assertEqual(events[-1][0], 'ready')
        self.assertEqual(events[-1][1][2], [720])

    def test_download_and_file(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'video.mkv'
            output.write_bytes(b'fixture')
            events = self.worker('print("PROGRESS:50%|1MiB/s|00:05"); print(' + repr('FILE:' + str(output)) + ')', 'download')
            self.assertEqual(events[0], ('progress', (50.0, '1MiB/s · 00:05')))
            self.assertEqual(events[-1], ('done', str(output)))

    def test_failed_probe_and_missing_file(self):
        events = self.worker('import sys; print("ERROR: unavailable"); sys.exit(1)')
        self.assertEqual(events[-1][0], 'error')
        self.assertIn('unavailable', events[-1][1])
        self.assertEqual(self.worker('print("FILE:/missing/video")', 'download')[-1][0], 'error')

    def test_cancel_before_start(self):
        self.assertEqual(self.worker('import time; time.sleep(30)', cancelled=True)[-1], ('cancelled', None))


if __name__ == '__main__':
    unittest.main()
