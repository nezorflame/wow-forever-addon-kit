#!/usr/bin/env python3
"""sv_bridge.py -- settings bridge for the WoW: Forever beta (Linux + Windows).
Derived from Thunderz96/forever-addon-kit (MIT); see README Credits.

The WoW: Forever beta client (build 1.60.x) writes addon SavedVariables on
exit / reload but never reads them back. The workaround: "!!ForeverCompat"
loads first and lists one seed file per bridged addon in its TOC, so the
saved globals exist before the real addon loads.

This script keeps the seeds in sync with what the client saves:

    WTF/Account/<acct>/SavedVariables/<Addon>.lua -> !!ForeverCompat/seeds/<Addon>.lua

Works on Linux (inotify) and Windows (100 ms polling). Paths: FOREVER_BETA_DIR and
FOREVER_ACCOUNT (env vars, or lines in ../forever.env) override the defaults /
auto-detection.

Modes:
    sync            one-shot: copy newer/valid saves into the seeds, rewrite TOC
    watch           file watcher (sub-second, needed to survive /reload)
    status          show seed vs saved file sizes and times
    seed FILE ADDON force a specific file in as the seed for ADDON

Bridged addons are discovered automatically: every folder in Interface/AddOns
whose TOC has a "## SavedVariables:" line (Blizzard_* and !!ForeverCompat
excluded). Seeds for removed addons are deleted (backup kept). The watcher also
monitors the AddOns folder, so installing/removing an addon takes effect live.

Safety: a seed is never replaced by a file under 25% of its size unless
--force (a broken session writes near-empty defaults). Replaced seeds are kept
in sv-backups/<Addon>/ (newest 40).
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
LOG = os.path.join(HERE, "sv_bridge.log")


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    if sys.stdout:  # pythonw.exe has no console
        print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


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

# Install location: FOREVER_BETA_DIR (env var or forever.env) overrides; else a per-platform default.
if os.environ.get("FOREVER_BETA_DIR"):
    BETA = os.environ["FOREVER_BETA_DIR"]
elif os.name == "nt":
    BETA = r"C:\Program Files (x86)\World of Warcraft\_classic_beta_"
else:
    BETA = os.path.expanduser("~/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_classic_beta_")


def detect_account():
    """WTF/Account/<id>#<n> folder. FOREVER_ACCOUNT env var overrides."""
    if os.environ.get("FOREVER_ACCOUNT"):
        return os.environ["FOREVER_ACCOUNT"]
    root = os.path.join(BETA, "WTF", "Account")
    try:
        cands = [d for d in os.listdir(root)
                 if os.path.isdir(os.path.join(root, d)) and d != "SavedVariables"]
    except OSError:
        cands = []
    hashed = [d for d in cands if "#" in d]
    cands = hashed or cands
    if len(cands) == 1:
        return cands[0]
    msg = (f"cannot pick the WTF account folder in {root}: {cands or 'none found'}; "
           "log in once, or set FOREVER_ACCOUNT=<folder name> (env or forever.env)")
    log("FATAL: " + msg)
    sys.exit(msg)


ACCOUNT = detect_account()
BETA_SV = os.path.join(BETA, "WTF", "Account", ACCOUNT, "SavedVariables")

COMPAT_SRC = os.path.join(PROJECT, "addons", "ForeverCompat")
COMPAT_DST = os.path.join(BETA, "Interface", "AddOns", "!!ForeverCompat")
SEEDS = os.path.join(COMPAT_DST, "seeds")
BACKUPS = os.path.join(PROJECT, "sv-backups")
ADDONS = os.path.join(BETA, "Interface", "AddOns")
# Never bridged: our own loader and Blizzard's addons (the client handles those).
EXCLUDE = {"!!ForeverCompat"}


def discover_bridged():
    """Addon folders whose TOC declares ## SavedVariables. The client names the
    saved file after the folder, so folder name == SavedVariables file name."""
    found = []
    try:
        entries = sorted(os.listdir(ADDONS))
    except OSError:
        return found
    for name in entries:
        if name in EXCLUDE or name.startswith("Blizzard_"):
            continue
        d = os.path.join(ADDONS, name)
        if not os.path.isdir(d):
            continue
        for toc in glob.glob(os.path.join(d, "*.toc")):
            try:
                text = open(toc, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if re.search(r"^##\s*SavedVariables\s*:", text, re.M | re.I):
                found.append(name)
                break
    return found


BRIDGED = discover_bridged()


PLACEHOLDER = "-- forever-addon-kit placeholder: waiting for this addon's first save\r\n"


def ensure_placeholders():
    """Create an empty seed for every bridged addon that has none yet.

    The WoW client only sees files that existed when it was launched; a seed
    created mid-session makes the next /reload log "Error loading seeds/X.lua"
    until a restart. A placeholder that exists from the start avoids that
    (its content is re-read on every reload, so later updates are fine)."""
    os.makedirs(SEEDS, exist_ok=True)
    created = False
    for a in BRIDGED:
        p = os.path.join(SEEDS, a + ".lua")
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(PLACEHOLDER)
            log(f"{a}: placeholder seed created")
            created = True
    return created


def rescan():
    """Refresh BRIDGED from the AddOns folder; drop seeds for removed addons."""
    global BRIDGED
    new = discover_bridged()
    if new != BRIDGED:
        added = sorted(set(new) - set(BRIDGED))
        gone = sorted(set(BRIDGED) - set(new))
        if added:
            log("addons added: " + ", ".join(added))
        if gone:
            log("addons removed: " + ", ".join(gone))
        BRIDGED = new
    changed = prune_seeds()
    return ensure_placeholders() or changed


def prune_seeds():
    """Remove seeds whose addon folder no longer exists. Returns True if any removed."""
    removed = False
    if not os.path.isdir(SEEDS):
        return False
    keep = set(BRIDGED)
    for f in os.listdir(SEEDS):
        if not f.lower().endswith(".lua"):
            continue
        addon = f[:-4]
        if addon not in keep:
            p = os.path.join(SEEDS, f)
            backup(addon, p)
            os.remove(p)
            log(f"{addon}: seed removed (addon folder gone), backup kept")
            removed = True
    return removed


TOC = """## Interface: 16001
## Title: |cffd2621fForever|r Compat + Settings Loader
## Notes: Retail API wrappers the Forever client lacks, plus a loader that restores addon settings the beta client never reads back. Managed by wow-forever-addon-kit/tools/sv_bridge.py.
## Author: Thunderz
## Version: 0.1.1

Compat.lua
ActionPlace.lua
{seeds}
"""

LUAC = shutil.which("luac") or shutil.which("luac5.4")


def valid_lua(path):
    """Reject a file caught mid-write. luac when present, else brace balance."""
    if LUAC:
        r = subprocess.run([LUAC, "-p", path], capture_output=True)
        return r.returncode == 0
    text = open(path, encoding="utf-8", errors="replace").read()
    return text.count("{") == text.count("}") and text.rstrip().endswith("}")


def backup(addon, path):
    d = os.path.join(BACKUPS, addon)
    os.makedirs(d, exist_ok=True)
    shutil.copyfile(path, os.path.join(d, time.strftime("%Y%m%d-%H%M%S") + ".lua"))
    for p in sorted(glob.glob(os.path.join(d, "*.lua")))[:-40]:
        os.remove(p)


def write_addon():
    os.makedirs(SEEDS, exist_ok=True)
    for name in ("Compat.lua", "ActionPlace.lua"):
        shutil.copyfile(os.path.join(COMPAT_SRC, name), os.path.join(COMPAT_DST, name))
    seeds = sorted(f for f in os.listdir(SEEDS) if f.lower().endswith(".lua"))
    toc = TOC.format(seeds="\n".join("seeds/" + s for s in seeds))
    tmp = os.path.join(COMPAT_DST, "!!ForeverCompat.toc.tmp")
    with open(tmp, "w", encoding="ascii", newline="\r\n") as f:
        f.write(toc)
    os.replace(tmp, os.path.join(COMPAT_DST, "!!ForeverCompat.toc"))
    return seeds


def put_seed(addon, src, force=False, why=""):
    dst = os.path.join(SEEDS, addon + ".lua")
    os.makedirs(SEEDS, exist_ok=True)
    if os.path.exists(dst):
        cur = open(dst, "rb").read()
        if cur == open(src, "rb").read():
            return False
        if cur.startswith(b"-- forever-addon-kit placeholder"):
            pass  # first real save replaces the placeholder, no guard, no backup
        elif not force and os.path.getsize(src) < 0.25 * os.path.getsize(dst):
            log(f"{addon}: REFUSED {os.path.getsize(src)} B over a {os.path.getsize(dst)} B seed "
                f"(looks like a defaults-only save). Use --force to accept.")
            return False
        else:
            backup(addon, dst)
    tmp = dst + ".tmp"
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)
    log(f"{addon}: seed updated from {why} ({os.path.getsize(dst)} B)")
    return True


def stable(path):
    """True once the file has stopped growing and parses as Lua."""
    try:
        s1 = os.path.getsize(path)
        time.sleep(0.05)
        s2 = os.path.getsize(path)
    except OSError:
        return False
    return s1 == s2 and s1 > 0 and valid_lua(path)


def sync(force=False, min_age=5):
    changed = rescan()
    for a in BRIDGED:
        sv = os.path.join(BETA_SV, a + ".lua")
        seed = os.path.join(SEEDS, a + ".lua")
        if not os.path.exists(sv):
            continue
        if os.path.exists(seed) and os.path.getmtime(sv) <= os.path.getmtime(seed) \
                and not open(seed, "rb").read().startswith(b"-- forever-addon-kit placeholder"):
            continue
        if time.time() - os.path.getmtime(sv) < min_age or not valid_lua(sv):
            continue  # still being written; next run will take it
        changed |= put_seed(a, sv, force=force, why="the client's last save")
    if changed or not os.path.exists(os.path.join(COMPAT_DST, "!!ForeverCompat.toc")):
        log("TOC lists: " + ", ".join(write_addon()))


def status():
    rescan()
    print("bridged (from AddOns/*/*.toc):", ", ".join(BRIDGED) or "(none)")
    for a in BRIDGED:
        for label, p in (("seed", os.path.join(SEEDS, a + ".lua")),
                         ("saved", os.path.join(BETA_SV, a + ".lua"))):
            if os.path.exists(p):
                print(f"  {a:<14} {label:<6} {os.path.getsize(p):>7} B  "
                      f"{time.strftime('%m-%d %H:%M:%S', time.localtime(os.path.getmtime(p)))}")
            else:
                print(f"  {a:<14} {label:<6} (missing)")


def handle_save(addon, p, last):
    """A bridged addon's SavedVariables file changed: wait until stable, copy to seed."""
    deadline = time.time() + 3
    while not stable(p) and time.time() < deadline:
        time.sleep(0.03)
    try:
        m = os.path.getmtime(p)
    except OSError:
        return
    if last.get(addon) == m:
        return
    last[addon] = m
    try:
        if put_seed(addon, p, why="the client's save (watch)"):
            write_addon()
    except Exception as e:  # noqa: BLE001
        log(f"{addon}: ERROR {e!r}")


def handle_addons_changed():
    time.sleep(0.5)
    sync(min_age=0)  # rescans, prunes, creates placeholders, picks up existing saves
    write_addon()
    log("AddOns changed; bridging: " + ", ".join(BRIDGED))


def watch():
    os.makedirs(BETA_SV, exist_ok=True)
    sync(min_age=0)
    if shutil.which("inotifywait") and not os.environ.get("FOREVER_FORCE_POLL"):
        log(f"sv_watch (inotify) started on {BETA_SV}; bridging: " + ", ".join(BRIDGED))
        watch_inotify()
    else:
        log(f"sv_watch (poll 100 ms) started on {BETA_SV}; bridging: " + ", ".join(BRIDGED))
        watch_poll()


def watch_inotify():
    proc = subprocess.Popen(
        ["inotifywait", "-m", "-q",
         "-e", "close_write", "-e", "moved_to", "-e", "create", "-e", "delete", "-e", "moved_from",
         "--format", "%w|%e|%f", BETA_SV, ADDONS],
        stdout=subprocess.PIPE, text=True)
    last = {}
    for line in proc.stdout:
        wdir, events, fname = line.rstrip("\n").split("|", 2)
        if os.path.normpath(wdir) == os.path.normpath(ADDONS):
            handle_addons_changed()
            continue
        if not fname.endswith(".lua"):
            continue
        addon = fname[:-4]
        if addon not in BRIDGED or "DELETE" in events or "MOVED_FROM" in events:
            continue
        handle_save(addon, os.path.join(BETA_SV, fname), last)


def watch_poll():
    """Portable watcher (Windows): poll SavedVariables mtimes every 100 ms and the
    AddOns folder listing every 2 s. The 100 ms cadence is what survives /reload
    (the client writes the save, then reloads addons ~1 s later)."""
    last = {}
    seen = {}
    for a in BRIDGED:
        p = os.path.join(BETA_SV, a + ".lua")
        seen[a] = os.path.getmtime(p) if os.path.exists(p) else 0
    addons_listing = set(os.listdir(ADDONS)) if os.path.isdir(ADDONS) else set()
    tick = 0
    while True:
        time.sleep(0.10)
        tick += 1
        for a in list(BRIDGED):
            p = os.path.join(BETA_SV, a + ".lua")
            try:
                m = os.path.getmtime(p)
            except OSError:
                continue
            if m != seen.get(a):
                seen[a] = m
                handle_save(a, p, last)
        if tick % 20 == 0 and os.path.isdir(ADDONS):
            now = set(os.listdir(ADDONS))
            if now != addons_listing:
                addons_listing = now
                handle_addons_changed()
                for a in BRIDGED:
                    p = os.path.join(BETA_SV, a + ".lua")
                    seen.setdefault(a, os.path.getmtime(p) if os.path.exists(p) else 0)


def main(argv):
    force = "--force" in argv
    args = [a for a in argv if not a.startswith("--")]
    mode = args[0] if args else "sync"
    if mode == "status":
        status()
    elif mode == "watch":
        watch()
    elif mode == "seed":
        if len(args) != 3:
            sys.exit("usage: sv_bridge.py seed FILE ADDON")
        src, addon = args[1], args[2]
        if not valid_lua(src):
            sys.exit(f"{src} does not parse as Lua")
        put_seed(addon, src, force=True, why=src)
        log("TOC lists: " + ", ".join(write_addon()))
    else:
        sync(force=force)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        import traceback
        log("FATAL: " + traceback.format_exc().strip().replace("\n", " | "))
        raise
