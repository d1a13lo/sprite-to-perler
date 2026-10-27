"""Create the original example sprites used in the user guide.

All artwork is drawn here from simple shapes (no third-party characters), so it
can be published with the guide. Run:  python docs/tools/make_examples.py
Output: docs/examples/
"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "examples"
OUTLINE = (24, 20, 28)


def ellipse(h, w, cy, cx, ry, rx):
    yy, xx = np.mgrid[0:h, 0:w]
    return ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0


def outlined(rgb, mask):
    """Add a one-pixel dark outline around the opaque area."""
    grown = mask.copy()
    grown[1:, :] |= mask[:-1, :]
    grown[:-1, :] |= mask[1:, :]
    grown[:, 1:] |= mask[:, :-1]
    grown[:, :-1] |= mask[:, 1:]
    rgb = rgb.copy()
    rgb[grown & ~mask] = OUTLINE
    return rgb, grown


def to_image(rgb, mask):
    a = np.dstack([rgb, np.where(mask, 255, 0).astype(np.uint8)])
    return Image.fromarray(a, "RGBA")


def mushroom():
    """'Pip' the mushroom: 40 x 40, transparent background (2 x 2 pegboards)."""
    h = w = 40
    rgb = np.zeros((h, w, 3), np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    cap = ellipse(h, w, 17, 19.5, 14, 17.5) & (yy <= 21)
    stem = (xx >= 11) & (xx <= 28) & (yy >= 19) & (yy <= 35) & ellipse(h, w, 27, 19.5, 11, 10)
    mask = cap | stem
    rgb[cap] = (216, 53, 58)
    rgb[cap & (xx + yy > 40)] = (170, 34, 46)                       # shade
    rgb[cap & ellipse(h, w, 9, 12, 4, 6)] = (242, 112, 107)           # highlight
    for cy, cx, r in [(9, 22, 3.2), (14, 9, 2.6), (15, 29, 3), (6, 14, 1.8), (18, 19, 1.8)]:
        rgb[cap & ellipse(h, w, cy, cx, r, r)] = (250, 244, 232)      # spots
    rgb[stem & ~cap] = (243, 227, 195)
    rgb[stem & ~cap & (xx >= 24)] = (217, 194, 154)
    for ex in (15, 23):                                               # eyes
        rgb[25:29, ex:ex + 2] = (24, 20, 28)
        rgb[25, ex] = (255, 255, 255)
    rgb[31, 18:22] = (190, 80, 90)                                    # smile
    rgb[30, 17] = rgb[30, 22] = (190, 80, 90)
    rgb[29:31, 12:14] = rgb[29:31, 26:28] = (240, 160, 150)           # cheeks
    rgb, mask = outlined(rgb, mask)
    return to_image(rgb, mask)


def slime(background, eye_shine):
    """'Glob' the slime, 30 x 22, on a solid background colour (no transparency)."""
    h, w = 24, 32
    rgb = np.zeros((h, w, 3), np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    body = ellipse(h, w, 15, 15.5, 10, 13) & (yy <= 21)
    rgb[body] = (92, 196, 112)
    rgb[body & (yy >= 16)] = (60, 150, 84)
    rgb[body & ellipse(h, w, 9, 9, 3, 4)] = (190, 240, 190)
    for ex in (11, 18):
        rgb[13:17, ex:ex + 2] = (24, 20, 28)
        rgb[13, ex] = eye_shine
    rgb, mask = outlined(rgb, body)
    rgb[~mask] = background
    return Image.fromarray(rgb, "RGB")


def star_frames():
    """Two-frame animated star, 24 x 24 (only the first frame is used)."""
    frames = []
    for size in (10.5, 8.5):
        h = w = 24
        yy, xx = np.mgrid[0:h, 0:w]
        ang = np.arctan2(yy - 12, xx - 12)
        rad = np.hypot(yy - 12, xx - 12)
        mask = rad <= size * (0.62 + 0.38 * np.cos(5 * (ang + np.pi / 2)) ** 2)
        rgb = np.zeros((h, w, 3), np.uint8)
        rgb[mask] = (255, 206, 64)
        rgb[mask & (xx + yy > 26)] = (230, 150, 40)
        rgb[mask & ellipse(h, w, 9, 10, 2, 2)] = (255, 246, 190)
        rgb, mask = outlined(rgb, mask)
        frames.append((rgb, mask))
    return frames


def save_gif(frames, path):
    images = []
    for rgb, mask in frames:
        colors = sorted(set(map(tuple, rgb[mask].tolist())))
        idx = np.full(mask.shape, len(colors), np.uint8)
        for i, c in enumerate(colors):
            idx[mask & np.all(rgb == c, axis=2)] = i
        img = Image.fromarray(idx, "P")
        img.putpalette([v for c in colors + [(0, 0, 0)] for v in c])
        img.info["transparency"] = len(colors)
        images.append(img)
    images[0].save(path, save_all=True, append_images=images[1:], duration=300, loop=0,
                   transparency=images[0].info["transparency"], disposal=2)


def landscape():
    """'Dusk Valley', 320 x 240: a large example (11 x 9 pegboards)."""
    h, w = 240, 320
    yy, xx = np.mgrid[0:h, 0:w]
    rgb = np.zeros((h, w, 3), np.uint8)
    sky = [(43, 33, 79), (69, 45, 105), (112, 61, 122), (168, 82, 120), (221, 116, 104), (246, 164, 98)]
    for i, c in enumerate(sky):
        rgb[yy >= i * 22] = c
    sun = ellipse(h, w, 130, 210, 34, 34)
    rgb[sun] = (255, 214, 120)
    rgb[sun & (yy > 125)] = (255, 190, 100)
    for amp, base, freq, color in [(28, 150, 0.031, (78, 52, 110)), (22, 172, 0.047, (52, 40, 86)),
                                   (16, 196, 0.069, (34, 30, 60))]:
        ridge = base - amp * (0.6 * np.sin(xx * freq) + 0.4 * np.sin(xx * freq * 2.3 + 1.1))
        rgb[yy >= ridge] = color
    for tx in range(8, w, 23):
        top = 200 - (tx * 7 % 17)
        tree = (np.abs(xx - tx) <= (yy - top) * 0.35) & (yy >= top) & (yy <= 232)
        rgb[tree] = (22, 44, 40)
    rgb[yy >= 226] = (20, 34, 32)
    stars = (np.random.default_rng(3).random((h, w)) > 0.996) & (yy < 70)
    rgb[stars] = (250, 240, 220)
    return Image.fromarray(rgb, "RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mushroom().save(OUT / "pip_mushroom.png")
    slime((255, 0, 255), (255, 255, 255)).save(OUT / "glob_slime_solid_background.png")
    slime((255, 255, 255), (255, 255, 255)).save(OUT / "glob_slime_white_background.png")
    save_gif(star_frames(), OUT / "twinkle_star_animated.gif")
    landscape().save(OUT / "dusk_valley_large.png")
    (OUT / "not_an_image.png").write_text("This is a text file with a .png name.\n")
    for p in sorted(OUT.iterdir()):
        print(p.name, Image.open(p).size if p.suffix != ".png" or p.stat().st_size > 100 else "")


if __name__ == "__main__":
    main()
