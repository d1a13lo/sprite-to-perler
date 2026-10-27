"""The editable artwork source (artwork/bead_template.psd) rebuilds the shipped bead-ring tile."""
import sys

import numpy as np

from conftest import ROOT
from perler_engine.render import ring_tile

sys.path.insert(0, str(ROOT / "tools"))
from build_assets import PSD, extract_ring_tile  # noqa: E402
from extract_psd_layers import read_layers  # noqa: E402


def test_template_layers_are_background_rings_and_guides_only():
    size, layers = read_layers(PSD)
    assert size == (4250, 4250)
    assert [layer["name"] for layer in layers] == ["BG", "HAMA BEADS", "PegBoardLines"]


def test_ring_tile_built_from_template_equals_shipped_asset():
    assert np.array_equal(extract_ring_tile(PSD), np.asarray(ring_tile()))
