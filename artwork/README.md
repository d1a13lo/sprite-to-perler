# Editable artwork source

`bead_template.psd` is the original Photoshop bead template created by d1a13lo. It is the
editable source of the bead-ring look used in every pattern.

| Item | Details |
|---|---|
| File | `bead_template.psd` — 4250 × 4250 px, 8-bit RGB, sRGB IEC61966-2.1 |
| SHA-256 | `9D11B117B2E8DC3E2E7071A356590F8986C894B305398CA1B8321A319B84FB4B` |
| Layers (bottom → top) | `BG` (dark background, #2B2B2B), `HAMA BEADS` (repeating 25 × 25 px bead-ring tile), `PegBoardLines` (white pegboard guide lines) |
| Contents | Only these three layers of simple geometric artwork: no sprites, characters, photos, logos or text |
| Metadata | Photoshop creation/save history (Photoshop CS6 and 24.1 version names, dates, document IDs); no personal names, e-mail addresses or file paths |

The file is distributed unchanged. "HAMA" in a layer name only describes the bead style; Hama is
a trademark of its owner and this project is not affiliated with it.

## License

Copyright © 2026 d1a13lo.

The bead template is part of Sprite-to-Bead Pattern and is licensed under the GNU General Public
License version 3 only (GPL-3.0-only); see [`../LICENSE`](../LICENSE).

## How the program uses it

The program does not read the PSD. It uses `perler_engine/assets/bead_ring_tile.png`, one 25 × 25
tile cut unchanged from the `HAMA BEADS` layer. To rebuild that tile from this file:

```
.venv\Scripts\python.exe tools\build_assets.py
```

`tools/build_assets.py` checks that the layer repeats exactly before it saves the tile, and
`tests/test_artwork.py` checks that the tile built from this file equals the one the program
ships. The pegboard lines are drawn by the program at the template's measured geometry (3 px white
lines every 725 px).
