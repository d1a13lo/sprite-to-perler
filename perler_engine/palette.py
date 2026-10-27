"""Informational Perler supply suggestions. Never changes the artwork.

Each original sprite colour is matched to the nearest solid Perler colour in
the bundled palette (a copy of the supplied perler_colors.csv) using
CIEDE2000 on CIELAB (sRGB, D65). Rules:
- only rows with finish "solid" and a digital colour value are matched; mixes,
  translucent, glow, metallic and pearl beads are listed as excluded;
- if the nearest colour is a photo estimate and a community-measured colour
  is within 1.5 delta-E of it, the measured colour is suggested instead;
- several original colours may share one Perler colour; their beads are added
  together (no forced unique assignment);
- with no usable palette, every bead is reported as unmatched, so supply
  quantities always add up to the total bead count.
"""
import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .errors import EngineError

PALETTE_PATH = Path(__file__).resolve().parent / "assets" / "perler_colors.csv"
MEASURED_TIE_WINDOW = 1.5   # delta-E within which measured data beats a photo estimate
CLOSE, APPROXIMATE = 5.0, 10.0  # match-quality bands (delta-E 2000)
REQUIRED_COLUMNS = {"family", "name_on_perler_com", "item_no", "finish", "hex", "r", "g", "b",
                    "hex_source", "confidence", "notes"}


class PaletteError(EngineError):
    """The Perler palette file is missing or unusable."""


@dataclass(frozen=True)
class PerlerColor:
    name: str
    code: str
    family: str
    finish: str
    rgb: tuple
    source: str
    confidence: str
    notes: str

    @property
    def hex(self):
        return "#%02X%02X%02X" % self.rgb

    @property
    def measured(self):
        return self.confidence == "community-measured"

    @property
    def photo_estimate(self):
        return self.confidence.startswith("low")


@dataclass(frozen=True, eq=False)
class Palette:
    colors: tuple       # matchable PerlerColor entries
    excluded: tuple     # (name, code, reason) for rows that are not matched
    path: Path


def load_palette(path=PALETTE_PATH):
    path = Path(path)
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        raise PaletteError(f"Perler palette file is missing: {path}") from None
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise PaletteError(f"Perler palette file cannot be read: {path} ({exc})") from None
    if not rows or not REQUIRED_COLUMNS <= set(rows[0]):
        raise PaletteError(f"Perler palette file has missing columns: {path}")
    colors, excluded = [], []
    for row in rows:
        name, code = row["name_on_perler_com"].strip(), row["item_no"].strip()
        if row["finish"] != "solid":
            excluded.append((name, code, f"{row['finish']} finish (not a single solid color)"))
            continue
        try:
            rgb = tuple(int(row[k]) for k in "rgb")
            valid = all(0 <= v <= 255 for v in rgb) and row["hex"].upper() == "#%02X%02X%02X" % rgb
        except ValueError:
            valid = False
        if not name or not valid:
            excluded.append((name, code, "missing or inconsistent digital color value"))
            continue
        colors.append(PerlerColor(name, code, row["family"], row["finish"], rgb,
                                  row["hex_source"], row["confidence"], row["notes"]))
    if not colors:
        raise PaletteError(f"Perler palette file has no usable solid colors: {path}")
    return Palette(tuple(colors), tuple(excluded), path)


# --- colour science -------------------------------------------------------------------

def srgb_to_lab(rgb):
    """sRGB (0-255, shape (..., 3)) to CIELAB, D65 white, 2 degree observer."""
    c = np.asarray(rgb, dtype=float) / 255.0
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = linear @ m.T / np.array([0.95047, 1.0, 1.08883])
    d = 6 / 29
    f = np.where(xyz > d ** 3, np.cbrt(xyz), xyz / (3 * d * d) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def ciede2000(lab1, lab2):
    """CIEDE2000 colour difference; inputs broadcast over (..., 3)."""
    L1, a1, b1 = np.moveaxis(np.asarray(lab1, dtype=float), -1, 0)
    L2, a2, b2 = np.moveaxis(np.asarray(lab2, dtype=float), -1, 0)
    c_bar7 = ((np.hypot(a1, b1) + np.hypot(a2, b2)) / 2) ** 7
    g = 0.5 * (1 - np.sqrt(c_bar7 / (c_bar7 + 25.0 ** 7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    zero = c1p * c2p == 0
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh))
    dh = np.where(zero, 0, dh)
    d_hp = 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(dh / 2))
    hsum = h1p + h2p
    h_bar = np.where(zero, hsum,
                     np.where(np.abs(h1p - h2p) <= 180, hsum / 2,
                              np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2)))
    t = (1 - 0.17 * np.cos(np.radians(h_bar - 30)) + 0.24 * np.cos(np.radians(2 * h_bar))
         + 0.32 * np.cos(np.radians(3 * h_bar + 6)) - 0.20 * np.cos(np.radians(4 * h_bar - 63)))
    l_bar, c_barp = (L1 + L2) / 2, (c1p + c2p) / 2
    s_l = 1 + 0.015 * (l_bar - 50) ** 2 / np.sqrt(20 + (l_bar - 50) ** 2)
    s_c = 1 + 0.045 * c_barp
    s_h = 1 + 0.015 * c_barp * t
    r_t = (-np.sin(np.radians(60 * np.exp(-((h_bar - 275) / 25) ** 2)))
           * 2 * np.sqrt(c_barp ** 7 / (c_barp ** 7 + 25.0 ** 7)))
    dl, dc, dhh = (L2 - L1) / s_l, (c2p - c1p) / s_c, d_hp / s_h
    return np.sqrt(dl ** 2 + dc ** 2 + dhh ** 2 + r_t * dc * dhh)


# --- matching ------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceMatch:
    rgb: tuple
    beads: int
    color: object      # PerlerColor, or None when unmatched
    delta_e: float     # nan when unmatched
    note: str = ""

    @property
    def hex(self):
        return "#%02X%02X%02X" % self.rgb


@dataclass(frozen=True)
class SupplyLine:
    color: object      # PerlerColor, or None for the unmatched line
    beads: int
    sources: tuple     # original rgb tuples combined into this line
    max_delta_e: float


@dataclass(frozen=True, eq=False)
class SupplyReport:
    sources: tuple     # SourceMatch per original colour, most beads first
    supplies: tuple    # SupplyLine per Perler colour (+ unmatched), most beads first
    total: int
    palette: object = field(default=None)
    error: str = ""    # why nothing could be matched, if the palette was unusable

    @property
    def unmatched_beads(self):
        return sum(s.beads for s in self.supplies if s.color is None)


def match_quality(delta_e):
    if np.isnan(delta_e):
        return "unmatched"
    return "close" if delta_e < CLOSE else "approximate" if delta_e <= APPROXIMATE else "weak"


def suggest_supplies(color_counts, palette, error="", chunk=2048):
    """Build the informational supply report for [(rgb, beads)] colour counts."""
    sources = []
    if palette is None or not palette.colors:
        sources = [SourceMatch(rgb, n, None, float("nan"), "no palette available")
                   for rgb, n in color_counts]
    else:
        plab = srgb_to_lab([c.rgb for c in palette.colors])
        measured = np.array([c.measured for c in palette.colors])
        for start in range(0, len(color_counts), chunk):
            part = color_counts[start:start + chunk]
            lab = srgb_to_lab([rgb for rgb, _ in part])
            d = ciede2000(lab[:, None, :], plab[None, :, :])
            for (rgb, n), row in zip(part, d):
                best = int(np.argmin(row))
                note = ""
                if palette.colors[best].photo_estimate:
                    within = np.nonzero(measured & (row - row[best] <= MEASURED_TIE_WINDOW))[0]
                    if len(within):
                        alt = int(within[np.argmin(row[within])])
                        note = (f"measured {palette.colors[alt].name} chosen over photo-estimated "
                                f"{palette.colors[best].name} (ΔE {row[alt]:.1f} vs {row[best]:.1f})")
                        best = alt
                sources.append(SourceMatch(rgb, n, palette.colors[best], float(row[best]), note))
    lines = {}
    for s in sources:
        beads, rgbs, worst = lines.get(s.color, (0, [], 0.0))
        worst = worst if np.isnan(s.delta_e) else max(worst, s.delta_e)
        lines[s.color] = (beads + s.beads, rgbs + [s.rgb], worst)
    supplies = sorted((SupplyLine(color, beads, tuple(rgbs), worst if color else float("nan"))
                       for color, (beads, rgbs, worst) in lines.items()),
                      key=lambda l: (l.color is None, -l.beads, l.color.name if l.color else ""))
    total = sum(n for _, n in color_counts)
    assert sum(l.beads for l in supplies) == total
    return SupplyReport(tuple(sources), tuple(supplies), total, palette, error)


def supply_report_for(grid, palette_path=PALETTE_PATH):
    """Supply report for a bead grid; an unusable palette gives an all-unmatched report."""
    try:
        palette = load_palette(palette_path)
    except PaletteError as exc:
        return suggest_supplies(grid.color_counts(), None, error=str(exc))
    return suggest_supplies(grid.color_counts(), palette)
