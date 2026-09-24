# Third-party notices

## forever-addon-kit (Thunderz)

Until tag `sv-bridge-final` this repo redistributed `addons/ForeverCompat/` and a
SavedVariables bridge derived from <https://github.com/Thunderz96/forever-addon-kit>
(MIT, Copyright (c) 2026 Thunderz). Both were retired on 2026-09-25 when beta build
1.60.1.70009 started reading SavedVariables again; nothing from that project remains in
the current tree. The MIT notice is preserved in the tagged history.

## Addons referenced by tools/patch_addons.py

The patches modify the user's own installed copies of Baganator and Syndicator
(<https://github.com/TheMouseNest>), SimpleItemLevel and NoAutoClose. No code from those
addons is redistributed here; the script only contains the few replaced lines needed to
locate and guard them.
