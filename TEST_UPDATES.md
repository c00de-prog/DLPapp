# Testing DLPapp updates

## Real Windows end-to-end test: 2.0.0 to 2.0.1

1. Keep a copy of the previous **2.0.0 DLPapp.exe** in a separate writable folder, for example `D:\DLPapp-update-test\DLPapp.exe`. Version 1 does not have an in-app updater.
2. First run the supplied 2.0.1 EXE manually to check the redesigned UI and normal downloading, then close it. This does not publish anything.
3. Copy the source ZIP's DLPapp folder contents into your repository root, preserve your license and commit/push the changes.
4. Create a GitHub release tagged **v2.0.1**, targeting that source commit. Attach the new executable with the exact name **DLPapp.exe** and optionally DLPapp.exe.sha256. Mark it as the latest published stable release. Drafts and prereleases are not returned by the production latest-release endpoint.
5. Start the old 2.0.0 EXE from the test folder. In Settings, save a recognizable nickname, language and download parent folder. Record these values.
6. Open **Settings → Updates → Check updates now**. This manual button bypasses the daily schedule. The latest API must report v2.0.1, an uploaded DLPapp.exe asset and a SHA256 digest.
7. Expect “DLPapp 2.0.1 is available”. Click **Download & restart** and confirm. The update is downloaded with progress, verified, staged, and installed after the old GUI exits.
8. After restart, check About says 2.0.1. Verify nickname, language, download folder and history are retained. The EXE should remain in the test folder. Settings stay in `%LOCALAPPDATA%\DLPapp\settings.json`.
9. Check again: the app should report no newer stable release.

Both copies share the same per-user settings. Do not run them concurrently for this test. Back up settings.json first if you want to restore your earlier preferences. This test uses a published public release and a real EXE replacement.

## Cancellation test

With the old test EXE, begin the update and cancel while downloading. Expect the old EXE and settings to remain usable. After a successful update, restore the saved old test EXE if you want to repeat the test. Do not rename the release asset to DLPapp-2.0.1.exe: the updater searches for DLPapp.exe.

## Read-only diagnostic for source users

On a developer computer with Python, run from the source folder:

```powershell
py -3 check_updates.py --current 2.0.0
```

This checks the real API and compares against an explicitly supplied version without changing VERSION, downloading an EXE, modifying settings or installing anything. It prints the tag, asset size and SHA256 if an update is available.

A release with the same or lower version will correctly show no update. Setting a higher tag alone is not enough: the executable's internal VERSION must match its release tag, otherwise the restart handshake will reject it.

## Offline logic tests

```powershell
py -3 -m unittest discover -s tests -v
```

Tests cover version comparisons, wrong origins, missing digests, verified downloads, cancellation, corrupted downloads, atomic settings and preservation of files. These do not perform a Windows EXE replacement.

## Troubleshooting

- No update: check the latest API at https://api.github.com/repos/c00de-prog/DLPapp/releases/latest and compare its tag with About.
- No EXE found: attach an asset named DLPapp.exe, rather than only the automatic source ZIP.
- No SHA256: wait for asset upload to finish and inspect the API digest. Without a digest, the app refuses automatic installation and offers the release page.
- Replacement denied: move the test EXE to a user-writable folder outside Program Files and retry.
- Network/rate-limit error: retry later; manual checking still performs a real GitHub request.
- Restart failure: inspect `%LOCALAPPDATA%\DLPapp\update-error.log`. Keep the `.dlpapp-backup` file if rollback was unable to restore it.

The updater is idle after you exit. Automatic checking is due every 24 hours while running or on the next launch; manual checking does not require waiting 24 hours.
