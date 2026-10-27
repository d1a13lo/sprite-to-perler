"""Development tool: rebuild perler_engine/assets/bead_ring_tile.png from the PSD.

The 'HAMA BEADS' layer of the Photoshop template is a perfectly repeating
25x25 tile whose grid starts at the canvas origin. This script verifies that
periodicity across the whole layer and saves one tile, unchanged.

Usage:  python tools/build_assets.py
"""
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from extract_psd_layers import read_layers

ROOT = Path(__file__).resolve().parents[1]
PSD = ROOT / "artwork" / "bead_template.psd"
OUT = ROOT / "perler_engine" / "assets" / "bead_ring_tile.png"
PITCH = 25


def extract_ring_tile(psd_path=PSD):
    _, layers = read_layers(psd_path)
    ring = next(layer for layer in layers if layer["name"] == "HAMA BEADS")
    if ring["top"] % PITCH or ring["left"] % PITCH:
        raise ValueError("Ring layer origin is not on the 25 px bead grid")
    rgba = ring["rgba"]
    h, w = rgba.shape[:2]
    if h % PITCH or w % PITCH:
        raise ValueError("Ring layer size is not a whole number of tiles")
    tile = rgba[:PITCH, :PITCH]
    if not np.array_equal(rgba, np.tile(tile, (h // PITCH, w // PITCH, 1))):
        raise ValueError("Ring layer is not a uniform repeating tile")
    return tile


def main():
    tile = extract_ring_tile()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(tile, "RGBA").save(OUT)
    print(f"Wrote {OUT}")
    print("Pixel SHA-256:", hashlib.sha256(tile.tobytes()).hexdigest())


if __name__ == "__main__":
    main()
