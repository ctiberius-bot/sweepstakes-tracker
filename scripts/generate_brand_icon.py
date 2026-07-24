#!/usr/bin/env python3
"""Generate the raster SafeTracker shield used by browsers and search results."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "safetracker-icon.png"
SIZE = 512
image = Image.new("RGBA", (SIZE, SIZE), (247, 250, 249, 255))
draw = ImageDraw.Draw(image)
shield = [(82, 55), (430, 55), (451, 105), (426, 336), (353, 429), (256, 477), (159, 429), (86, 336), (61, 105)]
draw.polygon(shield, fill=(10, 88, 82, 255), outline=(4, 47, 46, 255), width=18)
inner = [(111, 89), (401, 89), (416, 121), (394, 318), (333, 396), (256, 436), (179, 396), (118, 318), (96, 121)]
draw.polygon(inner, fill=(15, 118, 110, 255), outline=(153, 246, 228, 255), width=8)
font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
font = ImageFont.truetype(font_path, 166)
label = "ST"
box = draw.textbbox((0, 0), label, font=font, stroke_width=3)
x = (SIZE - (box[2] - box[0])) / 2
y = 187 - box[1]
draw.text((x, y), label, font=font, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(4, 47, 46, 255))
OUT.parent.mkdir(parents=True, exist_ok=True)
image.save(OUT, optimize=True)
