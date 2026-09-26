#!/usr/bin/env python3
"""patch_addons.py -- idempotent source patches for third-party addons on the WoW: Forever beta.
Part of wow-forever-addon-kit (MIT).

Re-run after any addon update (the update overwrites the patched file):

    python3 patch_addons.py            apply all patches
    python3 patch_addons.py --check    report only

Patches:
  NoAutoClose NoAutoclose.lua
      NoAutoClose blacklists PlayerSpellsFrame from UISpecialFrames (unsafe: protected
      frame) and normally uses a secure Esc handler instead. On Forever that handler is
      disabled ("RE is dead") and the fallback inserts the frame anyway. Esc in combat
      then blocks PlayerSpellsFrame:Hide() from a tainted loop and blames a random
      addon (Chattynator, AtlasLoot, WhatsTraining...). Leave the frame to Blizzard.
  SimpleItemLevel addon.lua (2 patches)
      Forever's Blizzard_InspectUI replaced the global InspectPaperDollFrame_UpdateButtons
      with the mixin method InspectPaperDollFrame:UpdateButtons(). Retail live still has
      the global, so the addon calls/hooks it unconditionally -> nil call on inspect.
      Use whichever exists.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)


def load_env_file():
    """Read PROJECT/forever.env (KEY=VALUE lines) into os.environ for keys not already set.
    Keeps machine-specific paths out of the scripts and out of git."""
    p = os.path.join(PROJECT, "forever.env")
    try:
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), os.path.expanduser(v.strip().strip('"')))
    except OSError:
        pass


load_env_file()

if os.environ.get("FOREVER_BETA_DIR"):
    BETA = os.environ["FOREVER_BETA_DIR"]
elif os.name == "nt":
    BETA = r"C:\Program Files (x86)\World of Warcraft\_classic_beta_"
else:
    BETA = os.path.expanduser("~/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_classic_beta_")
ADDONS = os.path.join(BETA, "Interface", "AddOns")

PATCHES = [
    {
        "addon": "NoAutoClose",
        "file": "NoAutoclose.lua",
        "old": """local is4E = toc >= 16000 and toc < 20000
""",
        "new": """local is4E = toc >= 16000 and toc < 20000
-- forever-addon-kit patch: without the secure esc handler (disabled on Forever) the
-- blacklisted PlayerSpellsFrame would be pushed into UISpecialFrames; leave it to Blizzard.
if is4E then ns.ignore.PlayerSpellsFrame = true; end
""",
    },
    {
        "addon": "SimpleItemLevel",
        "file": "addon.lua",
        "old": """                InspectPaperDollFrame_UpdateButtons()
""",
        "new": """                -- forever-addon-kit patch: Forever's InspectUI moved this to a mixin method
                if InspectPaperDollFrame_UpdateButtons then
                    InspectPaperDollFrame_UpdateButtons()
                elseif InspectPaperDollFrame and InspectPaperDollFrame.UpdateButtons then
                    InspectPaperDollFrame:UpdateButtons()
                end
""",
    },
    {
        "addon": "SimpleItemLevel",
        "file": "addon.lua",
        "old": """    hooksecurefunc("InspectPaperDollFrame_UpdateButtons", function()
""",
        "new": """    -- forever-addon-kit patch: Forever's InspectUI moved this to a mixin method
    local hookInspectUpdateButtons = InspectPaperDollFrame_UpdateButtons
        and function(fn) hooksecurefunc("InspectPaperDollFrame_UpdateButtons", fn) end
        or function(fn) hooksecurefunc(InspectPaperDollFrame, "UpdateButtons", fn) end
    hookInspectUpdateButtons(function()
""",
    },
]


def apply(p, check_only):
    path = os.path.join(ADDONS, p["addon"], p["file"])
    label = f"{p['addon']}/{p['file']}"
    if not os.path.exists(path):
        return f"{label}: addon not installed, skipped"
    src = open(path, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in src else "\n"
    old, new = p["old"].replace("\n", nl), p["new"].replace("\n", nl)
    if new in src:
        return f"{label}: already patched"
    if old not in src:
        return f"{label}: PATTERN NOT FOUND (addon changed, update this script)"
    if check_only:
        return f"{label}: needs patch"
    open(path, "w", encoding="utf-8", newline="").write(src.replace(old, new, 1))
    return f"{label}: patched"


def main(argv):
    check_only = "--check" in argv
    bad = False
    for p in PATCHES:
        msg = apply(p, check_only)
        print(msg)
        bad |= "NOT FOUND" in msg or "needs patch" in msg
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
