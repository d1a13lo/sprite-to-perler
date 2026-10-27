# Perler palette provenance

File: `perler_engine/assets/perler_colors.csv` (129 rows). Every row records its source in the
`hex_source` and `confidence` columns. The app only *suggests* Perler colors for information; the
pattern always keeps the sprite's own colors.

| Source | Rows | What it provides |
|---|---|---|
| perler.com product listing (1,000-count bead bags, retrieved 24 October 2026) | all 129 | Color names, product codes, color families |
| BeadColors dataset (github.com/maxcleme/beadcolors), MIT License, "Copyright (c) 2020 maxcleme" | 95 | Community-measured digital color values (`confidence = community-measured`) |
| meltbead.com Perler chart, recorded as "sampled from Perler product photos" | 23 | Digital color estimates (`confidence = low - photo estimate, single source`) |
| none | 11 | Mixes, clear, glow, metallic and pearl beads: no single color value; never suggested |

## The 23 photo-estimated entries

All 23 are Perler colors released in 2026 (product codes PER176xx), which the BeadColors dataset
does not cover. The app marks them with `*` and calls them photo estimates.

| Color | Code | Value | | Color | Code | Value |
|---|---|---|---|---|---|---|
| Lipstick | PER17668 | #F94041 | | Teaberry | PER17662 | #D289AC |
| Amber | PER17647 | #D06134 | | Faded Rose | PER17661 | #B86D8C |
| Persimmon | PER17663 | #E18B7A | | Champagne | PER17658 | #E5C192 |
| Jade | PER17648 | #0ACF8D | | Oyster | PER17654 | #E1D19D |
| Capri Blue | PER17650 | #3AD3E3 | | Steel | PER17657 | #52575A |
| Colonial Blue | PER17660 | #71B8CE | | Iron | PER17667 | #413B34 |
| Seafoam | PER17651 | #B1CDCA | | Shark | PER17649 | #7E9685 |
| Indigo | PER17653 | #4B516F | | Wheat | PER17659 | #EAC18C |
| Deep Purple | PER17665 | #5B3D69 | | Beige | PER17666 | #BE815C |
| Violet | PER17664 | #A455C6 | | Toffee | PER17646 | #9F6435 |
| Violet Frost | PER17652 | #CFD0DE | | Khaki | PER17655 | #B9A569 |
| | | | | Seaweed | PER17656 | #A88345 |

**What is distributed:** only these numeric color values and the source credit. No photographs or
other content from meltbead.com or perler.com are included in this project.

**What meltbead.com says** (checked 25 October 2026):

- Its Perler chart, https://meltbead.com/colors/perler, lists these 23 values (for example
  Lipstick PER17668 #F94041, Jade PER17648 #0ACF8D, Capri Blue PER17650 #3AD3E3) and states
  that they "were sampled from Perler product photos". It says Perler "does not publish numeric
  color values" and that its other values come from the MIT-licensed BeadColors dataset.
- Its Terms of Service, https://meltbead.com/terms ("Last updated October 9, 2026"), state:
  "The site's original text, design, and software belong to Meltbead or their respective
  licensors." They do not address reuse or redistribution of the color data.

**Status — permission reported by the project owner:** on 25 October 2026 the project owner
stated that they already have permission from Meltbead to use these 23 color values. This
permission has not been independently verified, and its written terms and scope (for example,
whether it covers redistribution in this project's source code and Windows download) are not
recorded here. The values are unchanged.

**Also not established:** whether the 95 BeadColors values were taken from BeadColors directly or
from the meltbead.com chart, and which BeadColors revision they match (see
`BeadColors-ATTRIBUTION.md`).

## Limitations of all digital color values

Digital values are approximations of physical beads. They have not been checked against real
beads; lighting, screens and ironing change how colors look.
