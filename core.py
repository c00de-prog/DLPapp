"""Portable paths and yt-dlp CLI contract; no GUI dependencies."""
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit
from i18n import AppError


def app_dir():
    if os.environ.get('DLPAPP_HOME') and (getattr(sys, 'frozen', False) or hasattr(sys, 'dlpapp_home')):
        return Path(os.environ['DLPAPP_HOME']).resolve()
    if hasattr(sys, 'dlpapp_home'):
        return Path(sys.dlpapp_home).resolve()
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent


def validate_url(value):
    value = value.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise AppError('invalid_url')
    return value


def qualities(info):
    if info.get('_type') in ('playlist', 'multi_video') or info.get('entries') is not None:
        raise AppError('playlist')
    if info.get('is_live'):
        raise AppError('live')
    heights = set()
    for item in info.get('formats', []):
        if item.get('vcodec') not in (None, 'none') and isinstance(item.get('height'), (int, float)):
            heights.add(int(item['height']))
    if not heights:
        raise AppError('no_formats')
    return sorted(heights, reverse=True)


def base_command(root):
    suffix = '.exe' if os.name == 'nt' else ''
    tools = Path(getattr(sys, '_MEIPASS', root)) / 'tools'
    # An optional tools folder next to EXE permits manual upstream updates.
    if (root / 'tools' / ('yt-dlp' + suffix)).is_file():
        tools = root / 'tools'
    for name in ('yt-dlp', 'ffmpeg', 'ffprobe', 'deno'):
        if not (tools / (name + suffix)).is_file():
            raise AppError('missing_tool', name='tools/' + name + suffix)
    return [str(tools / ('yt-dlp' + suffix)), '--ignore-config', '--no-playlist', '--no-colors',
            '--encoding', 'utf-8', '--socket-timeout', '20', '--retries', '3', '--extractor-retries', '2',
            '--ffmpeg-location', str(tools), '--js-runtimes', 'deno:' + str(tools / ('deno' + suffix))]


def probe_command(root, url):
    return base_command(root) + ['--dump-single-json', '--skip-download', '--', validate_url(url)]


def download_command(root, url, height, folder):
    height = int(height)
    if height <= 0:
        raise AppError('select_quality')
    # Exact height: never silently substitute a lower quality.
    selector = f'bv[height={height}]+ba/b[height={height}]/bv[height={height}]'
    return base_command(root) + ['--newline', '--progress', '--progress-delta', '0.3',
        '--progress-template', 'download:PROGRESS:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s',
        '--print', 'after_move:FILE:%(filepath)s', '--windows-filenames', '--no-overwrites',
        '--merge-output-format', 'mkv', '-f', selector, '-P', str(folder),
        '-o', '%(title).160B [%(id)s].%(ext)s', '--', validate_url(url)]


def progress(line):
    if not line.startswith('PROGRESS:'):
        return None
    parts = line[9:].strip().split('|')
    try:
        percent = float(parts[0].strip().rstrip('%'))
    except ValueError:
        return None
    return max(0, min(100, percent)), ' · '.join(x.strip() for x in parts[1:])
