# Быстрый запуск DLPapp CLI 0.1.0

Эта CLI-версия отдельная от GUI 2.0.2. Команда называется dlpapp, Python-пакет — dlpapp-cli.

## macOS

Если Homebrew уже установлен:

```sh
brew install python pipx ffmpeg deno
pipx install ./dist/dlpapp_cli-0.1.0-py3-none-any.whl
pipx ensurepath
```

Откройте новый терминал:

```sh
dlpapp doctor
dlpapp
```

Команда работает из любой папки после настройки PATH. pipx устанавливает Python-зависимости из интернета. FFmpeg и Deno не встроены в wheel.

## Windows

```powershell
py -m pip install --user pipx
py -m pipx install .\dist\dlpapp_cli-0.1.0-py3-none-any.whl
py -m pipx ensurepath
```

Нужны Python 3.10+, FFmpeg/ffprobe и Deno (или поддерживаемая Node.js). Можно указать папку с инструментами:

```powershell
dlpapp config --tools-dir "D:\DLPapp\tools"
dlpapp doctor
dlpapp
```

Откройте новое окно PowerShell после ensurepath. Для будущего EXE используйте scripts/build_windows.py на Windows: он создаст папку dist/dlpapp, которую необходимо передавать целиком и добавить в пользовательский PATH. Готовый Windows EXE в этом архиве отсутствует.

## Debian / Ubuntu

```sh
sudo apt install ./dist/dlpapp_0.1.0_all.deb
dlpapp doctor
dlpapp
```

Дистрибутив установит зависимости yt-dlp и FFmpeg. Deno надо установить отдельно. Если системный yt-dlp устарел, используйте pipx + wheel вместо Debian-пакета. Не устанавливайте одновременно wheel и .deb без понимания, какая команда будет первой в PATH.

Репозиторий APT пока не опубликован. Команда sudo apt install dlpapp без локального файла ещё недоступна.

## Команды

```sh
dlpapp config --language ru --nickname Shoxi
dlpapp info "ССЫЛКА"
dlpapp download "ССЫЛКА" --quality 720 --format mp4
dlpapp audio "ССЫЛКА" --format mp3
dlpapp convert "video.mp4" --format flac
dlpapp help
```

По умолчанию загрузки идут в ~/Downloads/DDownloads. Качество 720 означает максимум 720p. IPv4 включён по умолчанию, настройка доступна через config --network auto.

## Публикация кода

В существующем репозитории создайте папку cli и скопируйте туда этот проект, исключив dist, build, *.egg-info и __pycache__. GUI не заменяйте. Сохраните собственную лицензию проекта и добавьте её к CLI перед публикацией. Wheel и .deb публикуйте в отдельном Release CLI v0.1.0; не меняйте версию GUI ради CLI.

Инструкции для GitHub Actions находятся в README.md. macOS и Windows требуют проверки на соответствующих системах. APT-пакет ещё не проверен установкой на чистой Debian/Ubuntu; данные о сетевых скачиваниях с сайтов в этой среде не проверялись.
