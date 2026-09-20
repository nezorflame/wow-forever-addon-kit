# Windows setup

The scripts in `tools/` run unchanged on Windows. They cover two things: the
SavedVariables bridge (the beta client never reads settings back) and the addon
source patches for Forever. `memwatch.sh` is Linux-only.

All commands below are for **PowerShell**. In cmd.exe, write `%LOCALAPPDATA%`
instead of `$env:LOCALAPPDATA` (PowerShell does not expand `%VAR%`; it would
create a folder literally named `%LOCALAPPDATA%`).

## 1. Prerequisites

- Python 3.10+ from python.org. Tick "Add python.exe to PATH" in the installer.
  `luac` is optional; without it the bridge validates saves by brace balance.
- Git (optional) or download the repo as a zip.

## 2. Get the kit

```powershell
git clone https://github.com/nezorflame/wow-forever-addon-kit "$env:LOCALAPPDATA\wow-forever-addon-kit"
cd "$env:LOCALAPPDATA\wow-forever-addon-kit"
```

If WoW is not in the default `C:\Program Files (x86)\World of Warcraft\_classic_beta_`,
copy `forever.env.example` to `forever.env` and set `FOREVER_BETA_DIR`.
The WTF account folder (`WTF\Account\<id>#<n>`) is auto-detected after the first login;
if you have several, set `FOREVER_ACCOUNT` there too.

## 3. First run (installs `!!ForeverCompat` and seeds)

Log in to the beta once so the SavedVariables exist, exit, then:

```powershell
python tools\sv_bridge.py sync --force
python tools\sv_bridge.py status
```

To carry settings over from another PC: copy
`Interface\AddOns\!!ForeverCompat\seeds\*.lua` from there into the same folder here
(after the first `sync`), or copy the whole `WTF` folder before the first sync.
Same Battle.net account = same `<id>#<n>` folder name.

## 4. Keep the watcher running (survives `/reload`)

One command registers a logon task with absolute paths, windowless, auto-restart:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install-windows-task.ps1
```

It prints the task state and the log tail. The first log line should be
`sv_watch (poll 100 ms) started`. Remove it later with the same command plus `-Uninstall`.

If you prefer Task Scheduler by hand: program = full path to `pythonw.exe`,
arguments = full path to `sv_bridge.py` in quotes followed by `watch`, start in =
the `tools` folder. Untick "Stop the task if it runs longer than", tick restart on
failure. The task shows nothing on screen; any startup failure (for example no
WTF account folder yet) is written to `tools\sv_bridge.log`.

## 5. Addon patches

After installing or updating a patched addon:
```powershell
python tools\patch_addons.py --check
python tools\patch_addons.py
```
`PATTERN NOT FOUND` on `--check` means the addon changed at that spot; usually the
author fixed it upstream, so that patch can be dropped.

## 6. In-game

- Interface → AddOns → tick "Load out of date AddOns" (or `/console checkAddonVersion 0`).
- Seeds are re-read on `/reload`; a brand-new addon's seed needs a client restart once
  (the client only sees files that existed at launch; placeholders cover this after the
  first run).

## 7. Removing it when Blizzard fixes the client

`tools\install-windows-task.ps1 -Uninstall`, delete `Interface\AddOns\!!ForeverCompat`.
The patches are harmless to leave; addon updates overwrite them anyway.
