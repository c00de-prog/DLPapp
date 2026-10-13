import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from . import __version__
from . import config as settings
from . import engine


def text(config, en, ru):
    return ru if settings.language(config) == 'ru' else en


def parser():
    p = argparse.ArgumentParser(prog='dlpapp', description='DLPapp CLI — video and audio downloads. Run without arguments for the menu.')
    p.add_argument('--version', action='version', version='DLPapp CLI ' + __version__)
    sub = p.add_subparsers(dest='action')
    info = sub.add_parser('info', help='Show available source qualities without downloading')
    info.add_argument('url')
    info.add_argument('--json', action='store_true', help='Print metadata as JSON')
    info.add_argument('--verbose', action='store_true')
    for name, formats in (('download', engine.VIDEO_FORMATS), ('audio', engine.AUDIO_FORMATS)):
        child = sub.add_parser(name, help='Download video' if name == 'download' else 'Extract audio from a video link')
        child.add_argument('url')
        child.add_argument('--format', choices=formats, default='mp4' if name == 'download' else 'mp3')
        child.add_argument('-o', '--output', help='Exact destination folder (no extra subfolder)')
        child.add_argument('--network', choices=('auto', 'ipv4', 'ipv6'))
        child.add_argument('--verbose', action='store_true')
        if name == 'download':
            child.add_argument('-q', '--quality', type=engine.quality, default='best', help='best or maximum height, e.g. 720p')
            child.add_argument('--codec', choices=('auto', 'h264', 'hevc', 'vp9', 'av1'), default='auto')
    convert = sub.add_parser('convert', help='Extract audio from a local video, offline')
    convert.add_argument('file', type=Path)
    convert.add_argument('--format', choices=engine.AUDIO_FORMATS, default='mp3')
    convert.add_argument('-o', '--output')
    conf = sub.add_parser('config', help='Show or save settings')
    conf.add_argument('--language', choices=('auto', 'ru', 'en'))
    conf.add_argument('--nickname')
    conf.add_argument('--output')
    conf.add_argument('--network', choices=('auto', 'ipv4', 'ipv6'))
    conf.add_argument('--tools-dir')
    conf.add_argument('--reset', action='store_true')
    sub.add_parser('doctor', help='Check Python, yt-dlp, FFmpeg and a JavaScript runtime')
    sub.add_parser('help', help='Troubleshooting and installation help')
    return p


def show_info(data):
    print(data.get('title') or data.get('id') or 'Video')
    print('ID\tHeight\tFPS\tContainer\tVideo codec\tAudio codec')
    for stream in data.get('formats', []):
        if stream.get('ext') in ('mhtml', 'html'):
            continue
        values = [stream.get('format_id'), stream.get('height') or 'audio', stream.get('fps') or '-',
                  stream.get('ext'), stream.get('vcodec'), stream.get('acodec')]
        print('\t'.join(str(x or '-') for x in values))


def help_text(config):
    if settings.language(config) == 'ru':
        return '''DLPapp CLI — помощь
Команда dlpapp без аргументов открывает меню в терминале.
dlpapp info "ССЫЛКА" — доступные качества без скачивания.
dlpapp download "ССЫЛКА" --quality 720 --format mp4
dlpapp audio "ССЫЛКА" --format mp3
dlpapp convert "video.mp4" --format flac — локальное аудио без интернета.
dlpapp config --nickname Shoxi --language ru
dlpapp doctor — проверка зависимостей.

Качество 720 означает максимум 720p, а не повышение разрешения.
По умолчанию IPv4. Сеть можно изменить: config --network auto.
При медленной проверке используйте --verbose. Не всякая задержка связана с IPv6.
Facebook 18+ может требовать входа; cookies и обход ограничений здесь не реализованы.
Загрузки: ~/Downloads/DDownloads или точная папка --output.
Настройки CLI отдельные от GUI. Никнейм хранится локально.
Ctrl+C — остановка; частичные загрузки обычно остаются для продолжения.
В меню выберите 0, чтобы выйти. Приложение не работает после выхода.
CLI запускает yt-dlp отдельно для каждой операции, постоянной сессии нет.
Обновление pipx: pipx upgrade dlpapp-cli (после публикации пакета).
Для локального wheel: pipx install --force ./dlpapp_cli-ВЕРСИЯ-py3-none-any.whl
Обновление только yt-dlp: pipx runpip dlpapp-cli install -U 'yt-dlp[default]'
APT: sudo apt install ./dlpapp_ВЕРСИЯ_all.deb
APT-репозиторий ещё не опубликован; apt install dlpapp без файла пока недоступен.
Не отключайте антивирус ради запуска; фиксируйте точное обнаружение для проверки.'''
    return '''DLPapp CLI — help
Run dlpapp without arguments to open the terminal menu.
dlpapp info "URL" — list qualities without downloading.
dlpapp download "URL" --quality 720 --format mp4
dlpapp audio "URL" --format mp3
dlpapp convert "video.mp4" --format flac — offline local audio extraction.
dlpapp config --nickname Shoxi --language en
dlpapp doctor — check dependencies.

Quality 720 is a maximum height, not upscaling.
IPv4 is the default; change it with config --network auto.
Use --verbose for slow checks. Not every delay is an IPv6 issue.
Facebook age restrictions may require login; cookies and restriction bypass are not implemented.
Downloads: ~/Downloads/DDownloads, or the exact --output folder.
CLI settings are separate from the GUI. Your nickname stays local.
Ctrl+C stops the operation; partial downloads are usually kept for resuming.
Choose 0 to exit the menu. Nothing keeps running after exit.
yt-dlp starts separately for each operation; persistent sessions are not implemented.
pipx updates: pipx upgrade dlpapp-cli (after the package is published).
Local wheel update: pipx install --force ./dlpapp_cli-VERSION-py3-none-any.whl
Update yt-dlp only: pipx runpip dlpapp-cli install -U 'yt-dlp[default]'
APT: sudo apt install ./dlpapp_VERSION_all.deb
No APT repository is published yet; apt install dlpapp without a file is not available.
Do not disable antivirus to run the app; record exact detections for review.'''


def doctor(config):
    print('DLPapp CLI', __version__, '|', sys.platform, '| Python', sys.version.split()[0])
    ok = True
    try:
        probe = engine.run(engine.downloader() + ['--version'], capture=True)
        if probe.returncode:
            ok = False
        print('yt-dlp:', probe.stdout.strip() or 'unavailable')
    except RuntimeError as exc:
        print(exc)
        ok = False
    for name in ('ffmpeg', 'ffprobe', 'deno', 'node'):
        print(name + ':', engine.tool(name, config) or 'not found')
    if not all(engine.tool(name, config) for name in ('ffmpeg', 'ffprobe')):
        ok = False
    if not (engine.tool('deno', config) or engine.tool('node', config)):
        print(text(config, 'Warning: YouTube may need Deno (recommended) or supported Node.js plus yt-dlp-ejs.',
                   'Предупреждение: YouTube может требовать Deno или поддерживаемую Node.js и yt-dlp-ejs.'))
        ok = False
    print('Settings:', settings.config_path())
    print('Downloads:', settings.output_folder(config))
    print('Network:', config['network'])
    return 0 if ok else 1


def convert(args, config):
    source = args.file.expanduser().resolve()
    if not source.is_file():
        raise ValueError('Local video file not found: ' + str(source))
    ffmpeg = engine.tool('ffmpeg', config)
    if not ffmpeg:
        raise RuntimeError('FFmpeg is missing. Run dlpapp doctor.')
    folder = settings.output_folder(config, args.output)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / (source.stem + '.' + args.format)
    if destination.resolve() == source or destination.exists():
        raise ValueError('Output already exists or matches the source: ' + str(destination))
    codecs = dict(mp3='libmp3lame', m4a='aac', wav='pcm_s16le', flac='flac', opus='libopus')
    cmd = [ffmpeg, '-hide_banner', '-nostdin', '-n', '-i', str(source), '-map', '0:a:0', '-vn', '-c:a', codecs[args.format], str(destination)]
    result = engine.run(cmd)
    if result.returncode:
        raise RuntimeError('Audio extraction failed. See FFmpeg output above.')
    print(destination)
    return 0


def execute(args, config):
    if args.action == 'help':
        print(help_text(config))
        return 0
    if args.action == 'doctor':
        return doctor(config)
    if args.action == 'config':
        new = settings.DEFAULTS.copy() if args.reset else config.copy()
        changed = args.reset
        for key in ('language', 'nickname', 'output', 'network', 'tools_dir'):
            value = getattr(args, key)
            if value is not None:
                if key in ('output', 'tools_dir') and value:
                    value = str(Path(value).expanduser().resolve())
                if key == 'nickname':
                    value = value.strip()[:40]
                new[key] = value
                changed = True
        if changed:
            settings.save(new)
        print(json.dumps(new, ensure_ascii=False, indent=2))
        print('Settings:', settings.config_path())
        return 0
    if args.action == 'info':
        data = engine.info(config, args.url, args.verbose)
        if args.json:
            print(json.dumps(data, ensure_ascii=False))
        else:
            show_info(data)
        return 0
    if args.action == 'convert':
        return convert(args, config)
    if args.network:
        config = {**config, 'network': args.network}
    engine.require_media_tools(config)
    folder = settings.output_folder(config, args.output)
    folder.mkdir(parents=True, exist_ok=True)
    cmd = engine.command(config, args.url, folder, args.action, args.format,
                         getattr(args, 'quality', 'best'), getattr(args, 'codec', 'auto'), args.verbose)
    print(text(config, 'Output folder: ', 'Папка загрузки: ') + str(folder), flush=True)
    result = engine.run(cmd)
    if result.returncode:
        raise RuntimeError('yt-dlp failed (exit ' + str(result.returncode) + '). See its output above.')
    print(text(config, 'Completed.', 'Готово.'))
    return 0


def menu():
    while True:
        config = settings.load()
        name = config.get('nickname')
        print('\nDLPapp CLI ' + __version__ + ((' | ' + name) if name else ''))
        print(text(config, '1. Video\n2. Audio from URL\n3. Available qualities\n4. Local video to audio\n5. Settings\n6. Help\n7. Doctor\n0. Exit',
                   '1. Скачать видео\n2. Аудио по ссылке\n3. Доступные качества\n4. Локальное видео в аудио\n5. Настройки\n6. Помощь\n7. Диагностика\n0. Выход'))
        choice = input('> ').strip()
        if choice == '0':
            return 0
        if choice not in ('1', '2', '3', '4', '5', '6', '7'):
            print(text(config, 'Choose 0–7.', 'Выберите 0–7.'))
            continue
        try:
            if choice in ('1', '2', '3'):
                url = input(text(config, 'Video URL: ', 'Ссылка на видео: ')).strip()
                if not url:
                    continue
                if choice == '3':
                    argv = ['info', url]
                else:
                    fmt = input(text(config, 'Format (Enter = mp4/mp3): ', 'Формат (Enter = mp4/mp3): ')).strip().lower() or ('mp4' if choice == '1' else 'mp3')
                    argv = ['download' if choice == '1' else 'audio', url, '--format', fmt]
                    if choice == '1':
                        height = input(text(config, 'Maximum quality (Enter = best): ', 'Максимальное качество (Enter = best): ')).strip() or 'best'
                        argv += ['--quality', height]
            elif choice == '4':
                source = input(text(config, 'Local video path: ', 'Путь к видеофайлу: ')).strip().strip('"')
                fmt = input(text(config, 'Audio format (Enter = mp3): ', 'Аудиоформат (Enter = mp3): ')).strip().lower() or 'mp3'
                argv = ['convert', source, '--format', fmt]
            elif choice == '5':
                print(json.dumps(config, ensure_ascii=False, indent=2))
                value = input(text(config, 'Nickname (Enter = keep): ', 'Никнейм (Enter = оставить): ')).strip()
                lang = input('Language / Язык [auto/en/ru] (Enter = keep): ').strip().lower()
                folder = input(text(config, 'Output folder (Enter = keep): ', 'Папка загрузки (Enter = оставить): ')).strip().strip('"')
                argv = ['config']
                if value:
                    argv += ['--nickname', value]
                if lang:
                    argv += ['--language', lang]
                if folder:
                    argv += ['--output', folder]
            else:
                argv = ['help' if choice == '6' else 'doctor']
            execute(parser().parse_args(argv), config)
        except (ValueError, RuntimeError, OSError) as exc:
            print('Error: ' + str(exc), file=sys.stderr)
        except SystemExit:
            # Invalid menu choices return to the menu instead of killing the CLI.
            pass


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == '--_yt-dlp':
        # Private dispatcher used by the frozen console executable.
        import yt_dlp
        return yt_dlp.main(argv[1:]) or 0
    try:
        if not argv:
            if not sys.stdin.isatty():
                parser().print_help()
                return 0
            return menu()
        args = parser().parse_args(argv)
        return execute(args, settings.load())
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('\nStopped.', file=sys.stderr)
        return 130
