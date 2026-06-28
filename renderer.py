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

_STYLE_DIRS = {
    "default": "tiles",
    "lietxia": "tiles_lietxia",
    "hongkong": "tiles_hongkong",
}


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


def _tile_path(tile, style="default"):
    """Get the image path for a tile in the given style."""
    s, n = tile
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    base = os.path.join(plugin_dir, _STYLE_DIRS.get(style, "tiles"))
    if s == "z":
        return os.path.join(base, f"z{n}.png")
    return os.path.join(base, f"{s}{n}.png")


def render_guess(history, target_tiles, output_path, style="default"):
    """Render the guess history as an image."""
    header_h = 32
    row_h = TILE_H + GAP * 2 + 4
    cols = 14
    img_w = PAD * 2 + cols * (TILE_W + GAP) - GAP
    img_h = PAD + header_h + max(1, len(history)) * row_h + PAD

    img = Image.new("RGB", (img_w, img_h), (245, 245, 248))
    draw = ImageDraw.Draw(img)
    font = _get_font(13)

    # Header row: positional markers
    y = PAD
    for i in range(cols):
        x = PAD + i * (TILE_W + GAP)
        is_last = i == 13
        outline_color = (255, 100, 100) if is_last else (180, 180, 185)
        fill_color = (255, 235, 235) if is_last else (210, 210, 215)
        draw.rectangle([x, y, x + TILE_W, y + TILE_H], fill=fill_color, outline=outline_color, width=2)

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

            tile_path = _tile_path(tile, style)
            if os.path.exists(tile_path):
                tile_img = Image.open(tile_path).convert("RGBA")
                tile_img = tile_img.resize((TILE_W - 2, TILE_H - 2), Image.LANCZOS)
                if bg:
                    bg_rect = Image.new("RGBA", (TILE_W, TILE_H), bg + (255,))
                    bg_rect.paste(tile_img, (1, 1), tile_img)
                    img.paste(bg_rect, (x, y), bg_rect)
                else:
                    img.paste(tile_img, (x + 1, y + 1), tile_img)
            else:
                if bg:
                    draw.rectangle([x, y, x + TILE_W, y + TILE_H], fill=bg)

        y += row_h

    img.save(output_path)
    return output_path


def render_rules(target_tiles, output_path, style="default"):
    """Render a rules/example image showing tile format with one row."""
    cols = 14
    img_w = PAD * 2 + cols * (TILE_W + GAP) - GAP
    img_h = PAD + 36 + TILE_H + 20 + 60

    img = Image.new("RGB", (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_title = _get_font(22)
    font_tip = _get_font(16)

    # Title
    title = "猜胡牌规则"
    bw = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((img_w - bw[2] + bw[0]) // 2, PAD - 2), title, fill=(40, 40, 40), font=font_title)

    # Sort tiles for display
    from .mahjong import hand_str
    sorted13 = sorted(target_tiles[:13], key=lambda t: ({"w":0,"p":1,"s":2,"z":3}[t[0]], t[1]))
    display_tiles = sorted13 + [target_tiles[13]]

    # Draw tiles
    y = PAD + 40
    for i, tile in enumerate(display_tiles):
        x = PAD + i * (TILE_W + GAP)
        is_last = i == 13
        tp = _tile_path(tile)
        if os.path.exists(tp):
            tile_img = Image.open(tp).convert("RGBA")
            tile_img = tile_img.resize((TILE_W - 2, TILE_H - 2), Image.LANCZOS)
            if is_last:
                bg_rect = Image.new("RGBA", (TILE_W, TILE_H), (255, 235, 235, 255))
                bg_rect.paste(tile_img, (1, 1), tile_img)
                img.paste(bg_rect, (x, y), bg_rect)
            else:
                img.paste(tile_img, (x + 1, y + 1), tile_img)

    # Tips
    tips = [
        "格式: w112233 s445566 p77  字牌: z東東東",
        "每次发 14 张牌，最后一张(红框)是河底牌",
        "猜对→赢 | 次数耗尽→输",
    ]
    ty = y + TILE_H + 12
    for tip in tips:
        draw.text((PAD + 4, ty), tip, fill=(80, 80, 80), font=font_tip)
        ty += 18

    img.save(output_path)
    return output_path
