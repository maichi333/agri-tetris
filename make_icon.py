"""
tetris.ico を Pillow で生成するスクリプト
複数サイズ（16, 32, 48, 256px）を1つの ICO にまとめる
"""
from PIL import Image, ImageDraw
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tetris.ico")

# ── ブロック色定義（fill色, ハイライト色, 影色） ──
BLOCK_COLORS = {
    "I": ((  0, 220, 240), ( 80, 255, 255), (  0, 120, 140)),
    "O": ((230, 200,   0), (255, 240,  80), (140, 120,   0)),
    "T": ((170,   0, 230), (220,  80, 255), ( 90,   0, 130)),
    "S": ((  0, 210,  60), ( 80, 255, 130), (  0, 120,  30)),
    "Z": ((230,  30,  30), (255, 100,  80), (130,   0,   0)),
    "J": (( 20,  80, 230), ( 80, 160, 255), (  0,  30, 130)),
    "L": ((230, 120,   0), (255, 180,  60), (130,  60,   0)),
}

BG_TOP   = ( 8,  12,  50)
BG_BOT   = (18,  28,  80)
GRID_COL = (30,  40,  90, 120)   # グリッド線（半透明）

# 4×4 グリッドに配置するブロック（" "=空）
LAYOUT = [
    ["J", "T", "T", "T"],
    ["J", " ", "T", " "],
    ["J", "S", "S", "Z"],
    ["L", "L", "S", "Z"],
]

def draw_block(draw, x, y, cell, kind):
    """1ブロックを立体感ありで描画"""
    fill, hi, shadow = BLOCK_COLORS[kind]
    b = max(2, cell // 8)   # ベベル幅

    if cell > b * 2:
        draw.rectangle([x + b, y + b, x + cell - 1, y + cell - 1], fill=shadow)
        draw.rectangle([x, y, x + cell - b - 1, y + cell - b - 1], fill=fill)
        draw.rectangle([x, y, x + cell - b - 1, y + b - 1], fill=hi)
        draw.rectangle([x, y, x + b - 1, y + cell - b - 1], fill=hi)
        dot = max(1, cell // 6)
        draw.rectangle([x + b + 1, y + b + 1,
                        x + b + dot, y + b + dot], fill=hi)
    else:
        draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=fill)

def make_frame(size):
    """指定サイズのテトリスアイコン画像を生成"""
    img  = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(img)

    # 背景グラデーション（上→下）
    for y in range(size):
        t = y / size
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (size - 1, y)], fill=(r, g, b, 255))

    # グリッド線
    cell = size // 4
    for i in range(1, 4):
        draw.line([(i * cell, 0), (i * cell, size - 1)], fill=GRID_COL, width=1)
        draw.line([(0, i * cell), (size - 1, i * cell)], fill=GRID_COL, width=1)

    # ブロック描画
    for gy in range(4):
        for gx in range(4):
            kind = LAYOUT[gy][gx]
            if kind != " ":
                draw_block(draw, gx * cell, gy * cell, cell, kind)

    return img

# 複数サイズを生成して ICO に保存
sizes  = [16, 32, 48, 256]
frames = [make_frame(s) for s in sizes]

frames[0].save(
    OUT,
    format="ICO",
    sizes=[(s, s) for s in sizes],
    append_images=frames[1:],
)
print(f"アイコン生成完了: {OUT}")
