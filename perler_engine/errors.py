"""Errors raised by the conversion engine. Messages are written for the user."""


class EngineError(Exception):
    """Base class for all conversion-engine errors."""


class InputError(EngineError):
    """The uploaded file cannot be used as a sprite."""


class BackgroundDecisionNeeded(EngineError):
    """The background cannot be removed automatically without a user decision.

    `color` is the candidate background colour (or None when there is no
    uniform candidate) and `interior_pixels` is how many pixels of that colour
    are not connected to the image border.
    """

    def __init__(self, message, color=None, interior_pixels=0):
        super().__init__(message)
        self.color = color
        self.interior_pixels = interior_pixels


class AssetError(EngineError):
    """A bundled template asset is missing or corrupted."""
