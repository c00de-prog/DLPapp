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
        self.assertIn('unavailable', str(events[-1][1]))
        self.assertEqual(self.worker('print("FILE:/missing/video")', 'download')[-1][0], 'error')

    def test_cancel_before_start(self):
        self.assertEqual(self.worker('import time; time.sleep(30)', cancelled=True)[-1], ('cancelled', None))


if __name__ == '__main__':
    unittest.main()

class CachedDownloadTests(unittest.TestCase):
    def owner(self):
        return SimpleNamespace(events=queue.Queue(), cancel=threading.Event(), process=None,
                               process_lock=threading.Lock(), _terminate=DLPapp._terminate)

    def test_cached_download_uses_json_and_removes_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script, output, record = root/'fake.py', root/'video.mkv', root/'record.json'
            output.write_bytes(b'fixture')
            script.write_text('import sys,json\nfrom pathlib import Path\np=sys.argv[sys.argv.index("--load-info-json")+1]\ni=json.loads(Path(p).read_text(encoding="utf-8"))\nPath('+repr(str(record))+').write_text(json.dumps([p,i,sys.argv]))\nprint('+repr('FILE:'+str(output))+')\n')
            owner = self.owner()
            DLPapp._worker(owner, [sys.executable,str(script),'--','https://example.com/x'], 'download', 'https://example.com/x', {'id':'x','title':'Тест'})
            path, info, argv = json.loads(record.read_text())
            self.assertFalse(Path(path).exists())
            self.assertEqual(info['id'], 'x')
            self.assertNotIn('https://example.com/x', argv)
            self.assertEqual(owner.events.get(), ('done',str(output)))

    def test_rate_limit_stops_instead_of_reextracting(self):
        owner = self.owner()
        DLPapp._worker(owner, [sys.executable,'-c','print("ERROR: HTTP Error 429: Too Many Requests")'], 'probe', 'https://example.com/x')
        kind, error = owner.events.get()
        self.assertEqual(kind,'error')
        self.assertEqual(error.key,'rate_limited')

    def test_expired_cached_stream_refreshes_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); script=root/'fake.py'; count=root/'calls'; output=root/'video.mkv'
            output.write_bytes(b'fixture')
            script.write_text('import sys\nfrom pathlib import Path\np=Path('+repr(str(count))+')\np.write_text(p.read_text()+"x" if p.exists() else "x")\nif "--load-info-json" in sys.argv:\n print("ERROR: HTTP Error 403: Forbidden"); sys.exit(1)\nprint('+repr('FILE:'+str(output))+')\n')
            owner=self.owner()
            DLPapp._worker(owner,[sys.executable,str(script),'--','https://example.com/x'],'download','https://example.com/x',{'id':'x'})
            self.assertEqual(count.read_text(),'xx')
            self.assertEqual(owner.events.get(),('done',str(output)))
