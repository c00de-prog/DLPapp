import json
import locale
import os
import sys
import tempfile
from pathlib import Path

APP_ID = 'DLPappCLI'
DEFAULTS = dict(app_id=APP_ID, schema=1, language='auto', nickname='', output='', network='ipv4', tools_dir='')


def config_path():
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local')))
        return base / APP_ID / 'settings.json'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support' / APP_ID / 'settings.json'
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'dlpapp-cli/settings.json'


def load(path=None):
    data = DEFAULTS.copy()
    try:
        saved = json.loads(Path(path or config_path()).read_text(encoding='utf-8'))
        if isinstance(saved, dict) and saved.get('app_id') == APP_ID:
            for key in ('language', 'nickname', 'output', 'network', 'tools_dir'):
                if isinstance(saved.get(key), str):
                    data[key] = saved[key]
    except (OSError, ValueError):
        pass
    if data['language'] not in ('auto', 'ru', 'en'):
        data['language'] = 'auto'
    if data['network'] not in ('auto', 'ipv4', 'ipv6'):
        data['network'] = 'ipv4'
    data['nickname'] = data['nickname'][:40]
    return data


def save(data, path=None):
    path = Path(path or config_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {**DEFAULTS, **data, 'app_id': APP_ID, 'schema': 1}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def language(config):
    if config['language'] != 'auto':
        return config['language']
    # LC_ALL takes precedence; Windows uses the UI language when available.
    try:
        if sys.platform == 'win32':
            import ctypes
            name = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), '')
        else:
            name = os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG') or locale.getlocale()[0] or ''
    except (ValueError, AttributeError, OSError):
        name = ''
    return 'ru' if name.lower().startswith('ru') else 'en'


def output_folder(config, explicit=None):
    if explicit:
        return Path(explicit).expanduser().resolve()
    if config['output']:
        return Path(config['output']).expanduser().resolve()
    # Stable across working directories. No output inside the installed package.
    return Path.home() / 'Downloads/DDownloads'
