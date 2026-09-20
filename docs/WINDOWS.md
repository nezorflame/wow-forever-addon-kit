# Windows setup

The scripts in `tools/` run unchanged on Windows. They cover two things: the
SavedVariables bridge (the beta client never reads settings back) and the addon
source patches for Forever. `memwatch.sh` is Linux-only.

## 1. Prerequisites

- Python 3.10+ from python.org. Tick "Add python.exe to PATH" in the installer.
  `luac` is optional; without it the bridge validates saves by brace balance.
- Git (optional) or download the repo as a zip.

## 2. Get the kit

```
git clone https://github.com/nezorflame/wow-forever-addon-kit %LOCALAPPDATA%\wow-forever-addon-kit
```

If WoW is not in the default `C:\Program Files (x86)\World of Warcraft\_classic_beta_`,
copy `forever.env.example` to `forever.env` and set `FOREVER_BETA_DIR`.
The WTF account folder (`WTF\Account\<id>#<n>`) is auto-detected after the first login;
if you have several, set `FOREVER_ACCOUNT` there too.

## 3. First run (installs `!!ForeverCompat` and seeds)

Log in to the beta once so the SavedVariables exist, exit, then:

```
cd %LOCALAPPDATA%\wow-forever-addon-kit\tools
python sv_bridge.py sync --force
python sv_bridge.py status
```

To carry settings over from another PC: copy
`Interface\AddOns\!!ForeverCompat\seeds\*.lua` from there into the same folder here
(after the first `sync`), or copy the whole `WTF` folder before the first sync.
Same Battle.net account = same `<id>#<n>` folder name.

## 4. Keep the watcher running (survives `/reload`)

Task Scheduler → Create Task:
- General: run only when user is logged on.
- Triggers: At log on.
- Actions: Start a program
  - Program: `pythonw.exe` (windowless), full path e.g.
    `C:\Users\<you>\AppData\Local\Programs\Python\Python312\pythonw.exe`
  - Arguments: `sv_bridge.py watch`
  - Start in: `%LOCALAPPDATA%\wow-forever-addon-kit\tools`
- Settings: untick "Stop the task if it runs longer than", tick "If the task fails, restart every 1 minute".

Or simpler: a shortcut in `shell:startup` with the same program, arguments and start-in.
Run the task once now (right-click → Run). The log is `tools\sv_bridge.log`;
its first line should say `sv_watch (poll 100 ms) started`.

## 5. Addon patches

After installing or updating a patched addon:
```
python patch_addons.py --check
python patch_addons.py
```
`PATTERN NOT FOUND` on `--check` means the addon changed at that spot; usually the
author fixed it upstream, so that patch can be dropped.

## 6. In-game

- Interface → AddOns → tick "Load out of date AddOns" (or `/console checkAddonVersion 0`).
- Seeds are re-read on `/reload`; a brand-new addon's seed needs a client restart once
  (the client only sees files that existed at launch; placeholders cover this after the
  first run).

## 7. Removing it when Blizzard fixes the client

Delete the scheduled task, delete `Interface\AddOns\!!ForeverCompat`. The patches are
harmless to leave; addon updates overwrite them anyway.
