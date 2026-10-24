"""Minimal color parsing without importing a plotting library."""


def hex2rgb(color: str) -> tuple[int, int, int]:
    """Parse six hexadecimal digits, optionally prefixed by '#', into byte channels.

    Raises ValueError for malformed input. Use rgb_normalized for drawing.
    """
    digits = color.removeprefix('#')
    if len(digits) != 6: raise ValueError('Expected a six-digit hexadecimal color')
    return int(digits[:2], 16), int(digits[2:4], 16), int(digits[4:], 16)


def rgb_normalized(color: str) -> tuple[float, float, float]:
    """Return Cairo-compatible channels in the closed interval [0, 1]."""
    red, green, blue = hex2rgb(color)
    return red/255, green/255, blue/255
