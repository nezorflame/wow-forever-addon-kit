# Third-party notices

## forever-addon-kit (Thunderz)

`addons/ForeverCompat/` (Compat.lua, ActionPlace.lua, the TOC template) and the
SavedVariables bridge design that `tools/sv_bridge.py` is derived from come from
<https://github.com/Thunderz96/forever-addon-kit>, used under its MIT License,
reproduced here as that license requires:

```
MIT License

Copyright (c) 2026 Thunderz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Addons referenced by tools/patch_addons.py

The patches modify the user's own installed copies of Platynator and Baganator
(<https://github.com/TheMouseNest>). No code from those addons is redistributed here;
the script only contains the few replaced lines needed to locate and guard them.
