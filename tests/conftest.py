import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def app_grid(path, **kwargs):
    """The bead grid the app lays out for a sprite file (empty outer margins removed)."""
    from perler_engine import crop_to_beads, load_sprite
    return crop_to_beads(load_sprite(path, **kwargs))


@pytest.fixture(autouse=True)
def fail_on_interface_errors(monkeypatch):
    """Qt only prints exceptions raised inside button/signal handlers; fail instead."""
    caught = []
    monkeypatch.setattr(sys, "excepthook", lambda *exc: caught.append(exc))
    yield
    assert not caught, f"Error inside an interface handler: {caught[0][1]!r}"
