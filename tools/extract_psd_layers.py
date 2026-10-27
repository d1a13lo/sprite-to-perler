"""Development tool: extract raw layer rasters from the Photoshop template.

Reads the PSD read-only and writes each layer as an RGBA PNG plus a JSON
summary of layer names, bounds, opacity and blend modes. No external PSD
library is needed; only 8-bit RGB PSD files (version 1) are supported, which
is what the supplied template uses.

Usage:  python tools/extract_psd_layers.py <template.psd> <output_dir>
"""
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read(self, n):
        chunk = self.data[self.pos:self.pos + n]
        if len(chunk) != n:
            raise ValueError("Unexpected end of PSD data")
        self.pos += n
        return chunk

    def unpack(self, fmt):
        return struct.unpack(">" + fmt, self.read(struct.calcsize(">" + fmt)))


def unpack_bits(data, expected):
    out = bytearray()
    i = 0
    while i < len(data) and len(out) < expected:
        n = data[i]
        i += 1
        if n < 128:
            out += data[i:i + n + 1]
            i += n + 1
        elif n > 128:
            out += bytes([data[i]]) * (257 - n)
            i += 1
    if len(out) != expected:
        raise ValueError(f"PackBits row decoded to {len(out)} bytes, expected {expected}")
    return bytes(out)


def decode_channel(raw, width, height):
    compression = struct.unpack(">H", raw[:2])[0]
    body = raw[2:]
    if width == 0 or height == 0:
        return np.zeros((height, width), np.uint8)
    if compression == 0:
        return np.frombuffer(body[:width * height], np.uint8).reshape(height, width)
    if compression == 1:
        counts = struct.unpack(f">{height}H", body[:2 * height])
        pos = 2 * height
        rows = []
        for count in counts:
            rows.append(unpack_bits(body[pos:pos + count], width))
            pos += count
        return np.frombuffer(b"".join(rows), np.uint8).reshape(height, width)
    if compression in (2, 3):
        a = np.frombuffer(zlib.decompress(body), np.uint8).reshape(height, width).copy()
        if compression == 3:
            a = np.cumsum(a, axis=1, dtype=np.uint8)
        return a
    raise ValueError(f"Unsupported channel compression {compression}")


def read_layers(path):
    r = Reader(Path(path).read_bytes())
    sig, version = r.read(4), r.unpack("H")[0]
    r.read(6)
    channels, height, width, depth, mode = r.unpack("HIIHH")
    if sig != b"8BPS" or version != 1 or depth != 8 or mode != 3:
        raise ValueError("Only 8-bit RGB PSD (version 1) files are supported")
    r.read(r.unpack("I")[0])  # colour mode data
    r.read(r.unpack("I")[0])  # image resources
    r.unpack("I")  # layer and mask section length
    layer_info_end = r.unpack("I")[0] + r.pos
    count = abs(r.unpack("h")[0])
    records = []
    for _ in range(count):
        top, left, bottom, right = r.unpack("iiii")
        chans = [r.unpack("hI") for _ in range(r.unpack("H")[0])]
        _, blend = r.read(4), r.read(4).decode("latin1")
        opacity, clipping, flags, _ = r.unpack("BBBB")
        extra_end = r.unpack("I")[0] + r.pos
        r.read(r.unpack("I")[0])  # layer mask data
        r.read(r.unpack("I")[0])  # blending ranges
        name_len = r.unpack("B")[0]
        name = r.read(name_len).decode("latin1")
        r.read((4 - (name_len + 1) % 4) % 4)
        # Prefer the Unicode name from additional layer info when present.
        while r.pos + 12 <= extra_end:
            _, key = r.read(4), r.read(4)
            size = r.unpack("I")[0]
            block = r.read(size)
            if key == b"luni":
                n = struct.unpack(">I", block[:4])[0]
                name = block[4:4 + 2 * n].decode("utf-16-be")
        r.pos = extra_end
        records.append(dict(name=name, top=top, left=left, bottom=bottom, right=right,
                            channels=chans, blend=blend, opacity=opacity,
                            clipping=clipping, hidden=bool(flags & 2)))
    for rec in records:
        w, h = rec["right"] - rec["left"], rec["bottom"] - rec["top"]
        planes = {}
        for cid, length in rec["channels"]:
            raw = r.read(length)
            if cid in (-1, 0, 1, 2):
                planes[cid] = decode_channel(raw, w, h)
        full = np.full((h, w), 255, np.uint8)
        rgba = np.dstack([planes.get(0, full), planes.get(1, full), planes.get(2, full),
                          planes.get(-1, full)])
        rec["rgba"] = rgba
    r.pos = layer_info_end
    return (width, height), records


def main():
    psd, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    size, records = read_layers(psd)
    summary = dict(canvas=size, layers=[])
    for i, rec in enumerate(records):
        rgba = rec.pop("rgba")
        rec.pop("channels")
        rec["file"] = f"layer_{i:02d}.png"
        if rgba.size:
            Image.fromarray(rgba, "RGBA").save(out / rec["file"])
        summary["layers"].append(rec)
        print(i, rec)
    (out / "layers.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
