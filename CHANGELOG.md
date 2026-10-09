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
