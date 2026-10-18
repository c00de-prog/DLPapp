"""Retryable GUI-start confirmation; compatible with the 2.0.0–2.0.2 installer."""
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from settings import atomic_json


class StartupAcknowledgement:
    def __init__(self, settings_file, version, after, executable, environment=None, writer=atomic_json):
        self.folder = Path(settings_file).resolve().parent
        self.version, self.after, self.executable = version, after, executable
        self.env = os.environ if environment is None else environment
        self.writer = writer
        self.attempts = 0

    def log(self, message):
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            path = self.folder / 'update-startup.log'
            # Bound the diagnostic log. Do not include environment contents or credentials.
            if path.exists() and path.stat().st_size > 128 * 1024:
                path.write_text('', encoding='utf-8')
            with path.open('a', encoding='utf-8') as stream:
                stream.write(datetime.now(timezone.utc).isoformat() + ' ' + message + '\n')
        except OSError:
            pass

    def attempt(self):
        value = self.env.get('DLPAPP_UPDATE_ACK')
        if not value:
            return False
        self.attempts += 1
        try:
            path = Path(value).resolve()
            if path.parent != (self.folder / 'updates').resolve() or not path.name.endswith('.ready.json'):
                self.log('Rejected acknowledgement path outside the update directory')
                return False
            token = self.env.get('DLPAPP_UPDATE_TOKEN', '')
            if token and not re.fullmatch('[a-f0-9]{32}', token):
                self.log('Rejected invalid update token')
                return False
            executable = self.executable()
            self.writer(path, dict(app_id='DLPapp', version=self.version, pid=os.getpid(),
                                   token=token, exe=str(executable or '')))
        except (OSError, ValueError) as exc:
            self.log('Confirmation write failed on attempt ' + str(self.attempts) + ': ' + str(exc))
            if self.attempts < 20:
                self.after(500, self.attempt)
            return False
        self.log('GUI confirmed startup, version ' + self.version)
        self.env.pop('DLPAPP_UPDATE_ACK', None)
        self.env.pop('DLPAPP_UPDATE_TOKEN', None)
        return True
