"""English/Russian UI strings and persisted language selection."""
import ctypes
import json
import locale
import os
from pathlib import Path

STRINGS = {
    'en': {
        'window': 'DLPapp • Video downloader', 'subtitle': 'Link. Quality. Done.',
        'url_label': '01  VIDEO LINK', 'quality_label': '02  QUALITY',
        'check': 'Check video', 'download': 'Download video', 'cancel': 'Cancel',
        'folder_button': 'Open Downloads folder ↗', 'idle': 'Paste a link to get started.',
        'no_video': 'No video selected', 'quality_hint': 'Available qualities appear after checking',
        'checking': 'Checking video availability…', 'starting': 'Starting download…',
        'ready': 'Video available. Choose a quality.', 'merging': 'Merging video and audio…',
        'done': 'Done! {name}', 'cancelled': 'Stopped. Partial files are kept for a retry.',
        'failed': 'The operation failed. You can try again.', 'stopping': 'Stopping…',
        'progress': '{percent}% · {detail}', 'video': 'Video', 'error_title': 'Error',
        'check_error': 'Unable to check video', 'download_error': 'Unable to download',
        'folder_title': 'Folder', 'close_title': 'Close DLPapp?',
        'close_question': 'Stop the current operation and close the application?',
        'settings_error': 'Language changed for this session, but settings could not be saved.',
        'invalid_url': 'Enter a full http:// or https:// link to one video.',
        'playlist': 'Use a link to an individual video, not a playlist.',
        'live': 'Live streams are not supported. Wait for the stream to finish.',
        'no_formats': 'No available video formats were found.', 'select_quality': 'Choose a quality.',
        'missing_tool': 'Missing tool: {name}. Rebuild the app or run setup_tools.py.',
        'no_metadata': 'The service did not return video information.',
        'missing_output': 'The download ended, but the finished file was not found.',
        'process_exit': 'yt-dlp exited with code {code}.',
    },
    'ru': {
        'window': 'DLPapp • Загрузка видео', 'subtitle': 'Ссылка. Качество. Готово.',
        'url_label': '01  ССЫЛКА НА ВИДЕО', 'quality_label': '02  КАЧЕСТВО',
        'check': 'Проверить видео', 'download': 'Скачать видео', 'cancel': 'Отмена',
        'folder_button': 'Открыть папку Downloads ↗', 'idle': 'Вставьте ссылку, чтобы начать.',
        'no_video': 'Видео ещё не выбрано', 'quality_hint': 'Качества появятся после проверки',
        'checking': 'Проверяю доступность видео…', 'starting': 'Начинаю скачивание…',
        'ready': 'Видео доступно. Выберите качество.', 'merging': 'Объединяю видео и звук…',
        'done': 'Готово! {name}', 'cancelled': 'Остановлено. Частичные файлы сохранены для повторной загрузки.',
        'failed': 'Не удалось завершить операцию. Можно повторить.', 'stopping': 'Останавливаю…',
        'progress': '{percent}% · {detail}', 'video': 'Видео', 'error_title': 'Ошибка',
        'check_error': 'Не удалось проверить видео', 'download_error': 'Не удалось скачать',
        'folder_title': 'Папка', 'close_title': 'Закрыть DLPapp?',
        'close_question': 'Остановить текущую операцию и закрыть приложение?',
        'settings_error': 'Язык изменён на этот сеанс, но настройки не удалось сохранить.',
        'invalid_url': 'Введите полную ссылку http:// или https:// на одно видео.',
        'playlist': 'Вставьте ссылку на отдельное видео, а не на плейлист.',
        'live': 'Прямые эфиры пока не поддерживаются. Дождитесь окончания трансляции.',
        'no_formats': 'Не удалось найти доступные видеоформаты.', 'select_quality': 'Выберите качество.',
        'missing_tool': 'Не найден инструмент: {name}. Пересоберите приложение или запустите setup_tools.py.',
        'no_metadata': 'Сервис не вернул сведения о видео.',
        'missing_output': 'Загрузка завершилась, но готовый файл не найден.',
        'process_exit': 'yt-dlp завершился с кодом {code}.',
    },
}


def translate(language, key, **values):
    return STRINGS.get(language, STRINGS['en'])[key].format(**values)


class AppError(ValueError):
    def __init__(self, key, **values):
        self.key, self.values = key, values
        super().__init__(translate('en', key, **values))

    def localized(self, language):
        return translate(language, self.key, **self.values)


def detect_language():
    if os.name == 'nt':
        try:
            return 'ru' if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3ff == 0x19 else 'en'
        except (AttributeError, OSError):
            pass
    name = locale.getlocale()[0] or ''
    return 'ru' if name.lower().startswith('ru') else 'en'


def settings_path():
    base = Path(os.environ['LOCALAPPDATA']) if os.environ.get('LOCALAPPDATA') else Path.home() / '.config'
    return base / 'DLPapp' / 'settings.json'


def load_language(path=None):
    path = path or settings_path()
    try:
        value = json.loads(path.read_text(encoding='utf-8')).get('language')
        if value in STRINGS:
            return value
    except (OSError, ValueError, AttributeError):
        pass
    return detect_language()


# Version 2 strings. Keys are identical for both supported languages.
_NEW = {
'video_info': ('Video information', 'Информация о видео'),
'options': ('Format & quality', 'Формат и качество'),
'format': ('Format', 'Формат'), 'quality': ('Quality', 'Качество'),
'codec': ('Video codec', 'Видеокодек'),
'codec_hint': ('Auto chooses an available source codec without video conversion.', 'Автоматический режим выбирает доступный кодек без конвертации видео.'), 'auto': ('Auto', 'Автоматически'),
'settings': ('Settings', 'Настройки'),
'close_settings': ('Close', 'Закрыть'), 'downloads': ('Downloads', 'Загрузки'),
'profile': ('Profile', 'Профиль'), 'general': ('General', 'Основные'),
'updates': ('Updates', 'Обновления'), 'about': ('About', 'О приложении'),
'nickname': ('Nickname (stored only on this PC)', 'Никнейм (хранится только на этом ПК)'),
'language': ('Language', 'Язык'), 'save': ('Save', 'Сохранить'),
'download_parent': ('Save inside DDownloads in this folder:', 'Сохранять в DDownloads внутри этой папки:'),
'browse': ('Browse…', 'Обзор…'), 'reset_folder': ('Use folder next to EXE', 'Использовать папку рядом с EXE'),
'folder_note': ('New downloads use this folder. Existing files are not moved.', 'Новые загрузки сохранятся сюда. Старые файлы не перемещаются.'),
'folder_now': ('Current folder: {folder}', 'Текущая папка: {folder}'),
'paste': ('Paste', 'Вставить'), 'copy': ('Copy', 'Копировать'),
'cut': ('Cut', 'Вырезать'), 'select_all': ('Select all', 'Выделить всё'),
'clipboard_empty': ('The clipboard has no text.', 'В буфере обмена нет текста.'),
'auto_updates': ('Check DLPapp updates every 24 hours', 'Проверять обновления DLPapp раз в 24 часа'),
'auto_ytdlp': ('Update yt-dlp automatically every 24 hours', 'Обновлять yt-dlp автоматически раз в 24 часа'),
'check_updates': ('Check updates now', 'Проверить обновления'),
'update_ytdlp': ('Update yt-dlp now', 'Обновить yt-dlp'),
'current_version': ('Current version: {version}', 'Текущая версия: {version}'),
'update_checking': ('Checking for updates…', 'Проверяю обновления…'),
'latest': ('You are using the latest stable version.', 'Установлена последняя стабильная версия.'),
'new_version': ('DLPapp {version} is available.', 'Доступна DLPapp {version}.'),
'install_update': ('Download & restart', 'Скачать и перезапустить'),
'release_page': ('Open release page', 'Открыть страницу релиза'),
'update_question': ('Download the update and restart DLPapp? Your settings and history will be kept.', 'Скачать обновление и перезапустить DLPapp? Настройки и история сохранятся.'),
'update_progress': ('Update: {percent}% · {speed:.1f} MiB/s', 'Обновление: {percent}% · {speed:.1f} МиБ/с'),
'update_installing': ('Update downloaded. Restarting…', 'Обновление скачано. Перезапускаю…'),
'update_cancelled': ('Update download cancelled.', 'Скачивание обновления отменено.'),
'update_failed': ('Update failed: {error}', 'Обновление не удалось: {error}'),
'no_release': ('No published release was found yet.', 'Опубликованный релиз пока не найден.'),
'rate_limit': ('GitHub request limit reached. Try again later.', 'Достигнут лимит запросов GitHub. Повторите позже.'),
'invalid_release': ('The release metadata or executable path is invalid.', 'Некорректные данные релиза или путь к EXE.'),
'missing_digest': ('The release has no SHA256 digest. Open its official page to download manually.', 'У релиза нет SHA256. Откройте официальную страницу для ручной загрузки.'),
'missing_asset': ('Release asset not found: {name}', 'В релизе нет файла: {name}'),
'hash_failed': ('Downloaded executable failed integrity verification. The old app was kept.', 'Скачанный EXE не прошёл проверку целостности. Старое приложение сохранено.'),
'windows_only': ('This feature is available in the Windows EXE.', 'Эта функция доступна в Windows EXE.'),
'ytdlp_done': ('yt-dlp is ready: {version}', 'yt-dlp готов: {version}'),
'ytdlp_updating': ('Updating yt-dlp…', 'Обновляю yt-dlp…'),
'wait_operation': ('Finish or cancel the current operation first.', 'Сначала завершите или отмените текущую операцию.'),
'about_text': ('DLPapp downloads video and audio using yt-dlp and FFmpeg. Choose a link, format, quality and folder. No Python installation is needed for the Windows EXE.', 'DLPapp скачивает видео и аудио с помощью yt-dlp и FFmpeg. Выберите ссылку, формат, качество и папку. Для Windows EXE установка Python не нужна.'),
'author': ('Author: {name}', 'Автор: {name}'),
'background': ('Hide & notify when done', 'Скрыть и уведомить по завершении'),
'background_hint': ('You can hide this window. DLPapp will notify you when the download finishes.', 'Можно скрыть окно. DLPapp уведомит, когда загрузка завершится.'),
'hide_question': ('Keep downloading in the background? Yes: hide to tray. No: stop and close. Cancel: stay here.', 'Продолжить загрузку в фоне? Да: скрыть в трей. Нет: остановить и закрыть. Отмена: остаться в окне.'),
'notification_done': ('Download completed', 'Загрузка завершена'),
'notification_error': ('Download failed', 'Загрузка не удалась'),
'open_file': ('Open file', 'Открыть файл'), 'open_folder': ('Open folder', 'Открыть папку'),
'history_empty': ('No downloads in the selected folder yet.', 'В выбранной папке пока нет загрузок.'),
'history_title': ('File', 'Файл'), 'history_date': ('Date', 'Дата'),
'history_format': ('Format', 'Формат'), 'file_missing': ('This file was moved or deleted.', 'Файл перемещён или удалён.'),
'clear_history': ('Clear history for this folder', 'Очистить историю этой папки'),
'clear_question': ('Clear this folder’s history? Files will stay on disk.', 'Очистить историю этой папки? Файлы останутся на диске.'),
'audio_only': ('Audio only · best source', 'Только аудио · лучший источник'),
'no_compatible': ('No streams match this format and codec. Choose another option.', 'Нет потоков для этого формата и кодека. Выберите другой вариант.'),
'unsupported_format': ('Unsupported format or codec.', 'Неподдерживаемый формат или кодек.'),
'codec_note': ('Codecs select source streams without re-encoding. Not every video offers every codec. MP4: H.264/HEVC/AV1; MKV: any; WebM: VP9/AV1. Audio formats are converted by FFmpeg.', 'Кодеки выбирают исходные потоки без перекодирования. Не все кодеки есть у каждого видео. MP4: H.264/HEVC/AV1; MKV: любой; WebM: VP9/AV1. Аудиоформаты конвертирует FFmpeg.'),
'settings_saved': ('Settings saved.', 'Настройки сохранены.'),
'processing': ('Processing with FFmpeg…', 'Обработка через FFmpeg…'),
'privacy': ('Nickname, settings and history stay on this PC. Update checks send no nickname to GitHub.', 'Никнейм, настройки и история хранятся на этом ПК. При проверке обновлений никнейм не отправляется на GitHub.'),
'update_schedule': ('Checks run at startup when due, then every 24 hours while DLPapp is open. Nothing runs after you quit.', 'Проверки выполняются при запуске, если прошло 24 часа, и затем раз в 24 часа, пока DLPapp открыт. После выхода фоновых проверок нет.'),
}
for _key, (_en, _ru) in _NEW.items():
    STRINGS['en'][_key], STRINGS['ru'][_key] = _en, _ru
STRINGS['en']['folder_button'] = 'Open DDownloads ↗'
STRINGS['ru']['folder_button'] = 'Открыть DDownloads ↗'
STRINGS['en']['settings_error'] = 'Could not save settings. Check write permissions.'
STRINGS['ru']['settings_error'] = 'Не удалось сохранить настройки. Проверьте права записи.'

# Keep compatibility with callers from v1 while preserving all v2 settings.
def save_language(language, path=None):
    if language not in STRINGS:
        raise ValueError('Unsupported language')
    from settings import Settings
    Settings(path).update(language=language)
