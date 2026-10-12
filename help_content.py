"""Offline bilingual FAQ. No network calls, tracking or account credentials."""
from version import VERSION

FAQ = [
('checking', 'Почему долго проверяется видео?', 'Why does checking a video take so long?',
 'Проверка получает страницу сайта и список потоков. В версиях 2.0.1 и ниже нет нашего исправления IPv4. На одном ПК проверка YouTube заняла 185,9 секунды, а с IPv4 — 2,6 секунды. В 2.0.2 IPv4 включён для проверки и скачивания. Это результат одного теста, а не гарантия скорости: сервер, сеть и ограничения сайта тоже влияют. Обновление yt-dlp и обновление DLPapp — разные операции.',
 'Checking retrieves the site page and available streams. Versions 2.0.1 and earlier do not include our IPv4 fix. On one PC a YouTube check took 185.9 seconds, compared with 2.6 seconds over IPv4. Version 2.0.2 uses IPv4 for checks and downloads. This is one test, not a speed guarantee: the server, network and site restrictions also matter. Updating yt-dlp and updating DLPapp are separate operations.'),
('speed', 'Почему медленно скачивается видео?', 'Why is the video download slow?',
 'Скорость зависит от сервера сайта, маршрута сети, Wi-Fi и других загрузок. Большие видео и высокое качество требуют больше времени. После загрузки DLPapp может объединять видео со звуком или конвертировать аудио через FFmpeg: на этом этапе работают диск и процессор, а не только интернет. Низкий номер версии сам по себе не доказывает причину медленной загрузки.',
 'Speed depends on the site server, network route, Wi-Fi and other downloads. Large videos and high quality take longer. After downloading, DLPapp may merge video and audio or convert audio using FFmpeg; this stage uses the disk and CPU as well. An older version alone does not prove the cause of a slow download.'),
('quality', 'Почему Quality пустой? Какие качества доступны?', 'Why is Quality empty? Which qualities are available?',
 'Вставьте ссылку и нажмите «Проверить видео». Качества появятся после успешного получения данных. При отмене или ошибке список остаётся пустым. Формат и кодек фильтруют доступные варианты: попробуйте кодек Auto или MKV. Программа показывает только качества исходного видео и не создаёт 1080p из 720p. Для аудиоформатов выбор разрешения видео отключён.',
 'Paste a link and click Check video. Qualities appear after a successful check. Cancellation or an error leaves the list empty. Format and codec filter the options: try Auto codec or MKV. Only source qualities are offered; the app does not create 1080p from 720p. Video resolution selection is disabled for audio formats.'),
('browser', 'Почему в браузере YouTube быстрый?', 'Why is YouTube fast in my browser?',
 'Браузер и yt-dlp используют разные способы подключения и запросы. Браузер может использовать кэш, cookies и уже открытые соединения. В нашем тесте принудительный IPv4 убрал большие задержки yt-dlp. Поэтому быстрый браузер не исключает проблему отдельного сетевого маршрута. DLPapp пока запускает отдельный процесс yt-dlp для каждой операции: постоянная сессия не реализована.',
 'The browser and yt-dlp use different connections and requests. A browser can use cache, cookies and existing connections. In our test forcing IPv4 removed large yt-dlp delays, so a fast browser does not rule out a problem with a particular network route. DLPapp still starts a separate yt-dlp process for each operation; a persistent session is not implemented.'),
('facebook', 'Facebook: Cannot parse data или ограничение 18+', 'Facebook: Cannot parse data or an 18+ restriction',
 'yt-dlp не смог извлечь данные видео из ответа Facebook. Причиной может быть изменение сайта, требование входа или возрастное ограничение. Обновление yt-dlp не гарантирует исправление. Проверьте, воспроизводится ли видео без входа в браузере. DLPapp не обходит ограничения 18+ и пока не поддерживает импорт cookies. Не отправляйте пароли или cookies автору приложения.',
 'yt-dlp could not extract video data from the Facebook response. Site changes, a login requirement or an age restriction may cause this. Updating yt-dlp does not guarantee a fix. Check whether the video plays without signing in. DLPapp does not bypass age restrictions and does not currently support cookie import. Do not send passwords or cookies to the app author.'),
('formats', 'Как скачать видео в аудиоформате? Что такое кодек?', 'How do I download audio? What is a codec?',
 'Выберите MP3, M4A, WAV, FLAC или Opus, проверьте ссылку и нажмите скачивание. Аудио извлекается с помощью FFmpeg. MP4, MKV и WebM — контейнеры; H.264, HEVC, VP9 и AV1 — видеокодеки. Auto выбирает совместимый доступный поток без перекодирования видео. Локальное извлечение аудио из файла на ПК в этой версии ещё не реализовано.',
 'Choose MP3, M4A, WAV, FLAC or Opus, check the link and download. FFmpeg extracts the audio. MP4, MKV and WebM are containers; H.264, HEVC, VP9 and AV1 are video codecs. Auto selects a compatible source stream without video re-encoding. Local audio extraction from a file on your PC is not implemented in this version.'),
('updates', 'Как работают обновления DLPapp и yt-dlp?', 'How do DLPapp and yt-dlp updates work?',
 'DLPapp проверяет стабильный Release в c00de-prog/DLPapp на GitHub. yt-dlp обновляется отдельно из официального yt-dlp/yt-dlp. Автопроверки выполняются при запуске, когда прошло 24 часа, и затем во время работы приложения. Ручная проверка не требует ожидания. Настройки хранятся отдельно от EXE. Если версия в Release не новее текущей, обновление не предлагается.',
 'DLPapp checks stable GitHub releases in c00de-prog/DLPapp. yt-dlp updates separately from the official yt-dlp/yt-dlp repository. Automatic checks run at startup when due after 24 hours, and while the app is open. Manual checks do not require waiting. Settings are stored separately from the EXE. A release must be newer than the installed version to be offered.'),
('backup', 'Появился backup или ошибка запуска обновления', 'A backup appeared or the update failed to start',
 'Backup — резервная копия прежнего EXE. Он создаётся перед заменой и удаляется после подтверждения запуска новой версии. Если появилась ошибка, не удаляйте файлы наугад. Откройте %LOCALAPPDATA%\\DLPapp\\update-error.log и сообщите его текст вместе с версией из «О приложении». Тайм-аут подтверждения не доказывает конкретную причину. Не запускайте старый install-*.ps1 вручную.',
 'The backup is a copy of the previous EXE. It is created before replacement and removed after the new GUI confirms startup. If an error appears, do not delete files at random. Open %LOCALAPPDATA%\\DLPapp\\update-error.log and report its text with the version from About. A confirmation timeout alone does not identify the cause. Do not manually rerun an old install-*.ps1 script.'),
('sha256', 'Что такое SHA256? Нужен ли отдельный файл?', 'What is SHA256? Do I need the separate file?',
 'SHA256 — контрольная сумма для проверки целостности файла. При обновлении DLPapp сравнивает скачанный EXE с суммой из GitHub API. Это не сертификат и не гарантия отсутствия вирусов. Пользователю достаточно EXE; .sha256 не требуется запускать. Сборщик создаёт .sha256 рядом с EXE, а обычный запуск приложения такой файл не создаёт.',
 'SHA256 is a checksum used to verify file integrity. During updates DLPapp compares the downloaded EXE with the GitHub API digest. It is not a certificate or a guarantee of malware-free content. Users only need the EXE; a .sha256 file is not executable. The builder creates it next to the EXE; running the app does not create one.'),
('antivirus', 'Антивирус обнаружил Trojan. Что делать?', 'My antivirus detected a Trojan. What should I do?',
 'Остановите запуск и запишите точное название угрозы и путь из журнала защиты. Упаковка и обновляющий загрузчик могут вызвать подозрение, но это не доказывает ложное срабатывание. Ноль обнаружений в онлайн-сканере тоже не гарантирует безопасность. Отсутствие цифровой подписи и предупреждение SmartScreen отличаются от обнаружения Trojan. Не отключайте защиту; отправьте тот же файл Microsoft для анализа предполагаемого ложного срабатывания.',
 'Stop running the app and record the exact detection name and path from Protection History. Packaging and the update launcher may trigger suspicion, but this does not prove a false positive. Zero online detections are not a safety guarantee either. Missing code signing and a SmartScreen warning differ from a Trojan detection. Do not disable protection; submit the same file to Microsoft for a suspected false-positive review.'),
('folders', 'Где файлы, история и настройки?', 'Where are downloads, history and settings?',
 'Загрузки сохраняются в DDownloads внутри выбранной папки. Без выбора используется папка рядом с EXE. При смене папки старые файлы не перемещаются; история показывает выбранную папку. Настройки и история хранятся в %LOCALAPPDATA%\\DLPapp\\settings.json. Никнейм хранится локально и не отправляется на GitHub. Кэш runtime нужен для повторного запуска без распаковки.',
 'Downloads are saved in DDownloads inside the selected folder, or next to the EXE by default. Changing folders does not move existing files; history shows the selected folder. Settings and history are stored in %LOCALAPPDATA%\\DLPapp\\settings.json. Your nickname stays local and is not sent to GitHub. The runtime cache avoids extraction on every launch.'),
('portable', 'Нужен Python? Как вставить ссылку и скрыть окно?', 'Do I need Python? How do I paste or hide the window?',
 'Готовый EXE содержит Python и инструменты; устанавливать Python отдельно не нужно. Сборка предназначена для Windows 10/11 x64. Первый запуск новой сборки распаковывает runtime. Ссылку можно вставить кнопкой, Ctrl+V или правой кнопкой мыши, в том числе на русской раскладке. Во время загрузки можно скрыть окно в трей; после завершения предусмотрено уведомление. Полный выход останавливает приложение.',
 'The packaged EXE includes Python and the tools; a separate Python installation is not needed. The build targets Windows 10/11 x64. The first launch of a new build extracts its runtime. Paste with the button, Ctrl+V or the context menu, including with a Russian keyboard layout. During a download you can hide the window to the tray and receive a completion notification. A full exit closes the app.')
]


def articles(language='en', query=''):
    ru = language == 'ru'
    query = query.strip().casefold()
    result = [(row[0], row[1 if ru else 2], row[3 if ru else 4]) for row in FAQ]
    return [row for row in result if not query or query in (row[1] + ' ' + row[2]).casefold()]


def greeting(language, nickname=''):
    name = str(nickname or '').strip()[:40]
    if language == 'ru':
        return (f'Дорогой {name}!' if name else 'Здравствуйте!') + f' Это помощь DLPapp {VERSION}.'
    return (f'Dear {name},' if name else 'Hello!') + f' welcome to DLPapp {VERSION} Help.'
