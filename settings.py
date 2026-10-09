"""Per-user, atomic, namespaced settings and bounded download history."""
import json
import os
import tempfile
import threading
from pathlib import Path
from i18n import settings_path
from version import APP_ID


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


class Settings:
    def __init__(self, path=None):
        self.path = Path(path or settings_path())
        self.lock = threading.RLock()
        self.data = dict(app_id=APP_ID, schema=2, nickname='', language='auto', download_parent='',
                         auto_updates=True, auto_ytdlp=True, last_app_check=0, last_ytdlp_check=0,
                         last_format='MP4', last_codec='auto', last_quality='', history=[])
        try:
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            # Migrate the previous release's language-only settings, but no other app's JSON.
            if isinstance(saved, dict) and (saved.get('app_id') == APP_ID or set(saved) == {'language'}):
                self.data.update({k: v for k, v in saved.items() if k in self.data})
        except (ValueError, OSError):
            pass
        self.data['app_id'], self.data['schema'] = APP_ID, 2
        for key in ('nickname', 'download_parent', 'last_format', 'last_codec', 'last_quality'):
            if not isinstance(self.data[key], str):
                self.data[key] = ''
        if self.data['language'] not in ('auto', 'en', 'ru'):
            self.data['language'] = 'auto'
        self.data['nickname'] = self.data['nickname'][:40]
        for key in ('auto_updates', 'auto_ytdlp'):
            if not isinstance(self.data[key], bool):
                self.data[key] = True
        for key in ('last_app_check', 'last_ytdlp_check'):
            if not isinstance(self.data[key], (int, float)):
                self.data[key] = 0
        if not isinstance(self.data['history'], list):
            self.data['history'] = []
        self.data['history'] = [x for x in self.data['history'] if isinstance(x, dict)
                                and all(isinstance(x.get(k), str) for k in ('path', 'title', 'folder'))][-300:]

    def get(self, key, default=None):
        with self.lock:
            return self.data.get(key, default)

    def update(self, **values):
        with self.lock:
            previous = self.data.copy()
            self.data.update(values)
            try:
                atomic_json(self.path, self.data)
            except OSError:
                self.data = previous
                raise

    def folder(self, root):
        parent = self.get('download_parent')
        return Path(parent).expanduser().resolve() / 'DDownloads' if parent else Path(root) / 'DDownloads'

    def record(self, file, title, folder, url, fmt):
        from datetime import datetime, timezone
        item = dict(path=str(Path(file).resolve()), title=title, folder=str(Path(folder).resolve()),
                    url=url, format=fmt, date=datetime.now(timezone.utc).isoformat(timespec='seconds'))
        with self.lock:
            history = [x for x in self.data['history'] if x['path'] != item['path']]
            self.update(history=(history + [item])[-300:])

    def history(self, folder):
        target = os.path.normcase(str(Path(folder).resolve()))
        with self.lock:
            return [x.copy() for x in reversed(self.data['history'])
                    if os.path.normcase(x['folder']) == target]
