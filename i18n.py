"""English/Russian UI strings and persisted language selection."""
import ctypes
import json
import locale
import os
import tempfile
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


def save_language(language, path=None):
    if language not in STRINGS:
        raise ValueError('Unsupported language')
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        stream.write(json.dumps({'language': language}))
        temporary = Path(stream.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
