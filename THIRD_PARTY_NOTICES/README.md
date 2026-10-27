# Third-party notices

Sprite-to-Bead Pattern is Copyright © 2026 d1a13lo and licensed under the GNU General Public
License version 3 only (GPL-3.0-only; see [`../LICENSE`](../LICENSE)). That copyright covers the
project's own material only; the third-party software and data below keep their own copyrights
and licenses. The Windows download also contains the third-party software listed
below. Their license texts are in this folder, copied unchanged from the installed packages or from
the official sources named in each file.

## Components in the Windows download

| Component | Version | License | Text in this folder |
|---|---|---|---|
| Python (interpreter and standard library) | 3.13.16 | PSF License Agreement; bundled components under their own terms | `Python-3.13-LICENSE.txt` (the license file installed with Python: PSF license, Microsoft distributable code, bzip2, libffi, an Apache License 2.0 text, and a Tcl/Tk license although Tcl/Tk is not shipped) and `Python-3.13-INCORPORATED-SOFTWARE.txt` (expat, libmpdec, zlib, Mersenne Twister, SipHash, mimalloc, OpenSSL, the Unicode Character Database and the other components Python lists, plus HACL\*) |
| OpenSSL (`libcrypto-3.dll`, `libssl-3.dll`, used by Python's standard library) | 3.5.9 | Apache License 2.0; "Copyright 1998-2026 The OpenSSL Authors. All rights reserved." (from the DLLs' version information) | OpenSSL section of `Python-3.13-INCORPORATED-SOFTWARE.txt`; Apache License 2.0 text also in `Python-3.13-LICENSE.txt` |
| libffi (used by Python's `ctypes`) | as shipped with Python 3.13 | MIT-style ("Copyright (c) 1996-2022 Anthony Green, Red Hat, Inc and others") | included in `Python-3.13-LICENSE.txt` |
| Qt: Core, GUI, Widgets, SVG and Network libraries, with the Windows platform, style, image-format, icon-engine and touch plugins | 6.12.0 | GNU LGPL version 3; third-party code inside Qt under its own terms | `LGPL-3.0.txt` (+ `../LICENSE`, which LGPLv3 incorporates) and `Qt-6.12-THIRD-PARTY.md` |
| PySide6 and shiboken6 (Qt for Python) | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only (used here under LGPLv3); includes Python 3.7.0 source files under the PSF License | `LGPL-3.0.txt` and `Qt-6.12-THIRD-PARTY.md` |
| Mesa llvmpipe (`opengl32sw.dll`, software OpenGL renderer shipped with Qt) | as shipped with PySide6 6.12.0 | MIT License and Boost Software License 1.0 | `Qt-6.12-THIRD-PARTY.md` |
| Pillow | 13.0.0 | MIT-CMU (HPND); its bundled libraries (FreeType, HarfBuzz, libjpeg-turbo, libpng, libtiff, libwebp, Little CMS, libavif with dav1d and libyuv, OpenJPEG, Brotli, XZ, zlib-ng) under their own terms | `Pillow-13.0.0-LICENSE.txt` |
| FreeType (in Pillow; Qt GUI also lists FreeType) | 2.14.3 | FreeType License (FTL), chosen from FTL or GPLv2 | FTL text in `Pillow-13.0.0-LICENSE.txt` and `Qt-6.12-THIRD-PARTY.md`; credit below |
| Aileron Regular (Pillow's built-in default font, used for chart text) | as embedded in Pillow 13.0.0 | CC0 1.0 ("Aileron is No Rights Reserved", https://dotcolon.net/fonts/aileron) | — (no notice required) |
| NumPy, with OpenBLAS, LAPACK and the GCC runtime library | 2.5.4 | BSD-3-Clause; OpenBLAS BSD-3-Clause; LAPACK BSD-3-Clause-Open-MPI; GCC runtime library GPL-3.0-or-later WITH GCC-exception-3.1; and the other licenses listed in its file | `NumPy-2.5.4/` |
| PyInstaller bootloader | 6.22.3 | GPL-2.0-or-later with a special exception allowing distribution of programs built with it under any license | `PyInstaller-6.22.3-COPYING.txt` |
| Microsoft Visual C++ runtime (`VCRUNTIME140*.dll`, `MSVCP140*.dll`) | as shipped with Python, NumPy and PySide6 | Microsoft distributable code | described in `Python-3.13-LICENSE.txt` |

**FreeType credit** (required by the FreeType License):

> Portions of this software are copyright © 2026 The FreeType Project (https://freetype.org).
> All rights reserved.
>
> Sprite-to-Bead Pattern is based in part on the work of the FreeType Team.

*The FreeType License asks for "the value from the FreeType version you actually use"; Qt's
attribution for FreeType 2.14.3 gives "Copyright (c) 1996-2026"
(https://doc.qt.io/qt-6.12/qtgui-attribution-freetype.html).*

**Qt and PySide6 (LGPLv3).** The Qt and PySide6 libraries are included as separate, unmodified
files in the `_internal` folder of the Windows download, so they can be replaced with other
compatible versions. The source code of the exact versions used is available from The Qt Company:

- Qt 6.12.0: https://download.qt.io/official_releases/qt/6.12/6.12.0/single/
- PySide6 and shiboken6 6.12.0: https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/

Qt's summary of the LGPLv3 obligations is at https://doc.qt.io/qt-6/lgpl.html. These notices do
not by themselves establish that every LGPL condition is met; that depends on how the release is
packaged and has not been legally reviewed.

## Data and assets

| Item | Source | License / status |
|---|---|---|
| 95 Perler digital color values | BeadColors dataset (https://github.com/maxcleme/beadcolors) | MIT License, "Copyright (c) 2020 maxcleme" — see [`BeadColors-ATTRIBUTION.md`](BeadColors-ATTRIBUTION.md) and [`BeadColors-LICENSE.txt`](BeadColors-LICENSE.txt) |
| 23 Perler digital color values (2026 colors) | meltbead.com Perler chart, which states they "were sampled from Perler product photos" | Permission from Meltbead **reported by the project owner**, not independently verified; scope not recorded — see [`PALETTE-PROVENANCE.md`](PALETTE-PROVENANCE.md) |
| Perler color names and product codes | perler.com product listing | Factual product information; Perler is a trademark of its owner |
| Photoshop bead template, bead-ring overlay, application icon, example sprites, documentation | Sprite-to-Bead Pattern project (d1a13lo) | See [`PROJECT-ASSETS.md`](PROJECT-ASSETS.md) |

## Still unresolved

These points are **not** cleared by the notices in this folder:

1. **meltbead.com values.** meltbead.com's terms do not address reuse of its color data. The
   project owner reports having Meltbead's permission to use the 23 values; that permission has
   not been independently verified and its scope is not recorded (see `PALETTE-PROVENANCE.md`).
2. **Route of the 95 BeadColors values.** The meltbead.com chart also publishes BeadColors values;
   whether this project's 95 values were taken from BeadColors directly or through that chart has
   not been established, and the BeadColors revision used is not recorded.
3. **AI-generated material.** Rights in the ChatGPT-generated application icon, and in AI-assisted
   project material generally, depend on the services' terms and on local law (see
   `PROJECT-ASSETS.md`).
4. **Scope of the Qt list.** `Qt-6.12-THIRD-PARTY.md` includes every component Qt lists for the
   modules shipped, including ones Qt describes as optional or platform-specific; which of them
   are compiled into the Windows build has not been verified.
5. **Python's list** is described by Python itself as incomplete. For example, Python's `_lzma`
   module contains liblzma (XZ Utils), which the list does not mention; an XZ Utils license text
   is in `Pillow-13.0.0-LICENSE.txt` (section `xz-5.8.4`), but the version bundled with Python has
   not been verified.
6. **PySide6 file header.** Qt for Python's license page shows the header of its copied Python
   3.7.0 file (`bufferprocs_py37`) with `SPDX-License-Identifier: LicenseRef-Qt-Commercial`, while
   the installed PySide6 and shiboken6 packages declare `LGPL-3.0-only OR GPL-2.0-only OR
   GPL-3.0-only`. How these relate has not been clarified.
