"""Sprite-to-Perler conversion engine. Independent of any user interface."""
from .errors import AssetError, BackgroundDecisionNeeded, EngineError, InputError
from .layout import (BOARD_PEGS, BOARD_PX, PITCH, Layout, auto_layout, board_counts,
                     boards_needed)
from .render import render, save_png
from .sprite import BeadGrid, crop_to_beads, load_sprite, prepare_sprite

__all__ = [
    "AssetError", "BackgroundDecisionNeeded", "EngineError", "InputError",
    "BOARD_PEGS", "BOARD_PX", "PITCH", "Layout", "auto_layout", "board_counts",
    "boards_needed", "render", "save_png", "BeadGrid", "crop_to_beads", "load_sprite",
    "prepare_sprite",
]
