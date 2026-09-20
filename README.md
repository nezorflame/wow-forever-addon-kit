# wow-forever-addon-kit

Tools for running third-party addons on the **World of Warcraft: Forever** beta
(build line 1.60.x, interface `16001`), on Linux (Lutris / Proton) and Windows.

Three problems, three tools:

| Problem | Tool |
|---|---|
| The beta client **writes** addon SavedVariables but **never reads them back**, so every login and every `/reload` resets every addon to defaults. | `tools/sv_bridge.py` + the `!!ForeverCompat` loader addon |
| Some addons throw on Forever because it is a Retail-engine client without Retail content (no crafting orders, no Pet Journal, no range spells, ...). | `tools/patch_addons.py` |
| The client's GPU memory grows all session until the frame rate collapses. | `tools/memwatch.sh` (measurement only; the bug is Blizzard's) |

Everything here was measured against the live beta client, build 69913, September 2026.
Expect Blizzard to fix the first and third items eventually; see [Removing it](#removing-it).

## How the SavedVariables bridge works

A SavedVariables file is plain Lua that assigns globals. The client won't run it, but an
addon can. `!!ForeverCompat` sorts first in load order and lists one **seed** file per
addon in its TOC, so the globals exist before the real addon loads and it behaves as if
its settings had loaded. `sv_bridge.py` copies what the client saves on exit or `/reload`
back into the seeds, fast enough (sub-second) to land in the gap between "client wrote the
file" and "addons load again".

Bridged addons are discovered automatically: every folder in `Interface/AddOns` whose
TOC has a `## SavedVariables:` line. Seeds for removed addons are deleted (a backup is
kept), placeholder seeds are created up front so the client sees the files at launch,
and a save that is under 25% of the current seed's size is refused (a broken session
writes near-empty defaults). Account-wide SavedVariables only; per-character ones are
not bridged.

## Quick start (Linux)

```
git clone https://github.com/nezorflame/wow-forever-addon-kit ~/Git/wow-forever-addon-kit
cd ~/Git/wow-forever-addon-kit
cp forever.env.example forever.env   # set FOREVER_BETA_DIR to your _classic_beta_ folder
python3 tools/sv_bridge.py sync --force   # installs !!ForeverCompat, seeds from your saves
python3 tools/sv_bridge.py status
```

Keep the watcher running (needed to survive `/reload`):

```
cp tools/forever-sv-watch.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now forever-sv-watch.service
```

Requirements: Python 3.10+, `inotify-tools` (falls back to polling without it), `luac`
(optional, validates saves before copying). The loader addon targets interface `16001`, so
"Load out of date AddOns" is not needed for it; only for third-party addons whose TOC
does not list `16001` yet.

Windows: see [docs/WINDOWS.md](docs/WINDOWS.md).

### sv_bridge.py modes

| Command | Does |
|---|---|
| `sync` | one-shot: copy newer, valid saves into the seeds, rewrite the TOC |
| `sync --force` | same, ignoring the 25% size guard |
| `watch` | file watcher: inotify on Linux, 100 ms polling elsewhere |
| `status` | seed vs saved file sizes and times per addon |
| `seed FILE ADDON` | force a specific file in as the seed for ADDON |

Log: `tools/sv_bridge.log`. Replaced seeds: `sv-backups/<Addon>/` (newest 40).

## Addon patches

`tools/patch_addons.py` applies small, idempotent source guards to addons that break on
Forever. Addon updates overwrite them, so run it after every update:

```
python3 tools/patch_addons.py --check   # report only
python3 tools/patch_addons.py           # apply
```

`PATTERN NOT FOUND` on `--check` means the addon changed at that spot; so far that has
always meant the author fixed it upstream, and the patch was dropped from the script.

Current patches:

| Addon | Why |
|---|---|
| Platynator | LibRangeCheck finds no range spells on Forever, so the range checker is nil and nameplates with out-of-range fade or range colour rules throw. Treats "no checker" as in range. |
| Baganator | Blizzard's Forever `BankFrame.lua` calls `C_Bank.FetchNumPurchasedBankTabs(nil)` when Baganator's bank UI is in use (no Blizzard bank tab selected). Re-registers the callback with a nil guard. |

Retired (fixed upstream): Auctionator crafting-orders page (337), Baganator auctionable
check (827), Leatrix Plus Pet Journal hooks (1.60.03).

## GPU memory growth

`tools/memwatch.sh` samples the client every 30 s into `tools/memwatch.csv`: RSS, anonymous
memory, card-wide and **per-process** VRAM (DRM fdinfo), GPU busy, clocks and power. It
also archives the client's `Logs/gx.log` on exit, because that file is overwritten per
session and contains the game's own "Periodic Gpu Status Report: Mem Budget" line.

Findings on build 69913, D3D12 via vkd3d-proton, RX 9070 XT:
- Resident GPU memory grows ~40–70 MB/min for the whole session, linearly, no plateau.
- The game's own budget report and the driver's per-process figure agree, so it is the
  engine's own resource residency, not the translation layer.
- `/console gxRestart` releases it (a 2 s hiccup) and restores the frame rate. That is the
  practical mid-session fix. D3D11 showed no growth over a short test.

## Removing it

When a client build reads SavedVariables again: `systemctl --user disable --now
forever-sv-watch`, delete `Interface/AddOns/!!ForeverCompat`. The patches are harmless to
leave and disappear with the next addon update anyway.

## Credits

- **[Thunderz96/forever-addon-kit](https://github.com/Thunderz96/forever-addon-kit)** by
  Thunderz (MIT): discovered and proved the SavedVariables bug, wrote the `ForeverCompat`
  addon (`addons/ForeverCompat` here is a copy, with the TOC regenerated by the bridge)
  and the original Windows `sv_bridge.py` / `sv_watch.py` that `tools/sv_bridge.py` is
  derived from. This repo adds auto-discovery of bridged addons, placeholder seeds,
  seed pruning, an inotify watcher for Linux, and cross-platform path handling.
- **[TheMouseNest](https://github.com/TheMouseNest)** (plusmouse): Baganator, Syndicator,
  Platynator, Auctionator, Chattynator. The patches here are stopgaps; the author has
  been shipping Forever fixes within a day of reports.
- **[Gethe/wow-ui-source](https://github.com/Gethe/wow-ui-source)**, branch `forever`:
  Blizzard's Forever UI source (`Blizzard_UIPanels_Game/Camelot`), used to diagnose the
  bank frame crash.
- **[danielcosta42/guildos](https://github.com/danielcosta42/guildos)**: independent
  confirmation of the SavedVariables bug and the CVar-mirroring workaround idea.
- **[HansKristian-Work/vkd3d-proton](https://github.com/HansKristian-Work/vkd3d-proton)**
  issue tracker, for ruling the translation layer in and out.

## License

MIT, see [LICENSE](LICENSE). `addons/ForeverCompat` and the bridge design are
Copyright (c) 2026 Thunderz under MIT; that notice is reproduced in [NOTICE.md](NOTICE.md).
