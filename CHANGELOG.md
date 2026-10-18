# 2.0.3

- Reuse checked metadata for downloads via a temporary info JSON; reuse repeated checks for 10 minutes.
- Refresh expired cached streams once; stop retries on HTTP 429 and pause new GUI requests for 60 seconds.
- Disable automatic network/extractor/fragment retries and fix PowerShell test execution policy arguments.

- Check Windows notification delivery; restore hidden downloads with a fallback message when display is not confirmed.
- Add a bilingual Test notification button and notification diagnostics.

- Fix inherited PyInstaller environment during update restarts.
- Reset the frozen DLL search path before running the installer.
- Retry GUI startup acknowledgement and add installation/startup diagnostics.
- Add unique update confirmations, session installer locking, post-copy hashing and nondestructive rollback.
- Add Windows installer integration tests and manual migration instructions.

# 2.0.2

- Use IPv4 for yt-dlp checks and downloads.
- Add searchable offline Russian/English Help and nickname greetings.
- Explain current capabilities and troubleshooting without claiming antivirus safety or guaranteed speed.

# Changelog

## 2.0.1

- Center and limit main content width, including maximized windows.
- Add rounded cards and buttons, responsive scrolling and clearer disabled controls.
- Replace standard settings tabs with sidebar navigation and a compact save footer.
- Add an empty history state and remove bright table borders.
- Add TEST_UPDATES.md and check_updates.py for real update testing and read-only diagnostics.

## 2.0.0

- Redesign the lightweight Tkinter interface with dark cards and green controls.
- Add lazy Settings tabs: Profile, General, Downloads, Updates and About.
- Add local nickname, persisted language and download parent folder.
- Save completed files under DDownloads and show history for the selected folder.
- Add history file opening and clearing without deleting files.
- Fix Windows paste shortcuts on Russian keyboard layouts; add Paste and context menus.
- Add MP4, MKV, WebM, MP3, M4A, WAV, FLAC and Opus output.
- Filter qualities by source codec and container; persist recent format/codec/quality.
- Add background download hiding, native Windows tray and completion notifications.
- Check official DLPapp releases on a daily schedule and offer verified, staged EXE replacement.
- Update yt-dlp separately from its official releases, preserving it across app upgrades.
- Preserve settings and history with an explicit DLPapp identity and atomic JSON writes.
- Pass the original EXE location from the caching launcher for portable updates.
- Extend offline tests and document build, release and native Windows verification.
