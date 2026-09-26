# wow-forever-addon-kit

Tools for running third-party addons on the **World of Warcraft: Forever** beta
(build line 1.60.x, interface `16001`), on Linux (Lutris / Proton) and Windows.

| Problem | Tool |
|---|---|
| Some addons throw on Forever because it is a Retail-engine client without Retail content, or because a beta build renamed something they hardcode. | `tools/patch_addons.py` |

The SavedVariables bridge, the `SVProbe` test addon and the `memwatch.sh` GPU sampler,
retired when build 1.60.1.70009 fixed both bugs, are at tag `sv-bridge-final`.

## Setup

```
git clone https://github.com/nezorflame/wow-forever-addon-kit ~/Git/wow-forever-addon-kit
cd ~/Git/wow-forever-addon-kit
cp forever.env.example forever.env   # set FOREVER_BETA_DIR to your _classic_beta_ folder
```

Requirements: Python 3.10+. Runs unchanged on Windows (`py tools\patch_addons.py --check`
from PowerShell, with `forever.env` pointing at `C:\Program Files (x86)\World of Warcraft\_classic_beta_`).

## Addon patches

`tools/patch_addons.py` applies small, idempotent source guards to addons that break on
Forever. Addon updates overwrite them, so run it after every addon update and after every
client build:

```
python3 tools/patch_addons.py --check   # report only
python3 tools/patch_addons.py           # apply
```

`already patched` only means the patch text is present, not that it is still needed. To
find out, read the Blizzard file the patch works around in Blizzard's Forever UI source
([Gethe/wow-ui-source](https://github.com/Gethe/wow-ui-source), branch `forever`) after a
build bump, and the addon's own changelog after an addon update. `PATTERN NOT FOUND` on
`--check` means the addon changed at that spot, usually an upstream fix: drop the entry.

Current patches, each with the upstream issue to check before re-applying after an addon update:

| Addon | Upstream issue | Why |
|---|---|---|
| SimpleItemLevel | [kemayo/wow-simpleitemlevel#64](https://github.com/kemayo/wow-simpleitemlevel/issues/64) | Forever's `Blizzard_InspectUI` replaced the global `InspectPaperDollFrame_UpdateButtons` with the mixin method `InspectPaperDollFrame:UpdateButtons()`; Retail live still has the global, so the addon calls and hooks it unconditionally and inspecting a player throws. Uses whichever exists. |

## Credits

- **[Thunderz96/forever-addon-kit](https://github.com/Thunderz96/forever-addon-kit)** by
  Thunderz (MIT): discovered and proved the SavedVariables bug and wrote the loader addon
  and bridge this repo carried until tag `sv-bridge-final`.
- **[TheMouseNest](https://github.com/TheMouseNest)** (plusmouse): Baganator, Syndicator,
  Platynator, Auctionator, Chattynator. The patches here are stopgaps; the author has
  been shipping Forever fixes within a day of reports.
- **[Gethe/wow-ui-source](https://github.com/Gethe/wow-ui-source)**, branch `forever`:
  Blizzard's Forever UI source, used to check after each build whether a patch is still needed.
- **[danielcosta42/guildos](https://github.com/danielcosta42/guildos)**: independent
  confirmation of the SavedVariables bug.

## License

MIT, see [LICENSE](LICENSE). Third-party notices in [NOTICE.md](NOTICE.md).
