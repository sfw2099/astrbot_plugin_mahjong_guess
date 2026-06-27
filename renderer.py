"""Render mahjong guess results as images using PIL."""

import os
from PIL import Image, ImageDraw, ImageFont

TILE_W, TILE_H = 56, 72
GAP = 4
PAD = 20
COLOR_OK = (120, 220, 120)
COLOR_PRESENT = (240, 210, 80)
COLOR_ABSENT = (180, 180, 180)

_FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "STZHONGS.TTF")


def _get_font(size=14):
    if os.path.exists(_FONT_PATH):
        try:
            return ImageFont.truetype(_FONT_PATH, size)
        except Exception:
            pass
    for p in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _tile_path(tile):
    """Get the image path for a tile."""
    s, n = tile
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tiles")
    if s == "z":
        return os.path.join(base, f"z{n}.png")
    return os.path.join(base, f"{s}{n}.png")


def render_guess(history, target_tiles, output_path):
    """Render the guess history as an image.

    history: list of (guess_tiles_list, comparison_result)
    target_tiles: the winning hand tiles (for the last tile indicator)
    """
    max_guesses = 10
    header_h = 36
    row_h = TILE_H + GAP * 2 + 6
    cols = 14
    img_w = PAD * 2 + cols * (TILE_W + GAP) - GAP
    img_h = PAD + header_h + (len(history) + 1) * row_h + PAD

    img = Image.new("RGB", (img_w, img_h), (245, 245, 248))
    draw = ImageDraw.Draw(img)
    font = _get_font(13)

    # Header row: show tile images
    y = PAD
    for i in range(cols):
        x = PAD + i * (TILE_W + GAP)
        label = "河底" if i == 13 else ""
        if label:
            bw = draw.textbbox((0, 0), label, font=font)
            draw.text((x + (TILE_W - bw[2] + bw[0]) // 2, y + 4), label, fill=(120, 120, 130), font=font)
        draw.rectangle([x, y + 18, x + TILE_W - 1, y + 18 + TILE_H - 1], fill=(210, 210, 215), outline=(180, 180, 185))

    y += header_h

    # Guess rows
    for gi, (guess_tiles, comp_result) in enumerate(history):
        for i, (tile, status) in enumerate(comp_result):
            x = PAD + i * (TILE_W + GAP)
            bg = None
            if status == "correct":
                bg = COLOR_OK
            elif status == "present":
                bg = COLOR_PRESENT
            elif status == "absent":
                bg = COLOR_ABSENT

            tile_path = _tile_path(tile)
            if os.path.exists(tile_path):
                tile_img = Image.open(tile_path).convert("RGBA")
                tile_img = tile_img.resize((TILE_W - 2, TILE_H - 2), Image.LANCZOS)
                if bg:
                    bg_rect = Image.new("RGBA", (TILE_W, TILE_H), bg + (255,))
                    bx = (TILE_W - (TILE_W - 2)) // 2
                    by = (TILE_H - (TILE_H - 2)) // 2
                    bg_rect.paste(tile_img, (bx, by), tile_img)
                    img.paste(bg_rect, (x, y), bg_rect)
                else:
                    img.paste(tile_img, (x + 1, y + 1), tile_img)
            else:
                if bg:
                    draw.rectangle([x, y, x + TILE_W, y + TILE_H], fill=bg)
                label = f"{tile[0]}{tile[1]}"
                bw = draw.textbbox((0, 0), label, font=font)
                draw.text((x + (TILE_W - bw[2] + bw[0]) // 2, y + (TILE_H - 14) // 2), label, fill=(50, 50, 50), font=font)

        y += row_h

    img.save(output_path)
    return output_path
