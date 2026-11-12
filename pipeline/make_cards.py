"""Intro and outro cards for the explainer."""

import os

from PIL import Image, ImageDraw, ImageFont

OUT = r'E:\minimaxh3\out'
CARDS = os.path.join(OUT, 'cards')
FONT_B = r'C:\Windows\Fonts\msyhbd.ttc'
FONT_R = r'C:\Windows\Fonts\msyh.ttc'
W, H = 1920, 1080
ACCENT = (110, 170, 255)
TEXT = (240, 246, 255)
DIM = (150, 172, 205)

os.makedirs(CARDS, exist_ok=True)


def font(p, s):
    return ImageFont.truetype(p, s)


def scrim(top_alpha=170, bottom_alpha=210):
    """Dark gradient so titles read on top of any frame."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        a = int(top_alpha + (bottom_alpha - top_alpha) * (1 - abs(t - 0.5) * 2))
        d.line([(0, y), (W, y)], fill=(6, 10, 20, a))
    return img


def intro():
    img = scrim(70, 168)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 8], fill=ACCENT + (235,))

    title = '模型蒸馏'
    tf = font(FONT_B, 150)
    tw = d.textlength(title, font=tf)
    d.text(((W - tw) / 2, 330), title, font=tf, fill=TEXT)

    d.rectangle([(W - 260) / 2, 520, (W + 260) / 2, 525], fill=ACCENT + (230,))

    sub = '为什么 7B 能打 70B'
    sf = font(FONT_R, 58)
    sw = d.textlength(sub, font=sf)
    d.text(((W - sw) / 2, 570), sub, font=sf, fill=(214, 228, 250))

    tag = '三套做法 · 五步路线 · 效果与坑'
    gf = font(FONT_R, 36)
    gw = d.textlength(tag, font=gf)
    d.text(((W - gw) / 2, 690), tag, font=gf, fill=DIM)

    p = os.path.join(CARDS, 'intro.png')
    img.save(p)
    return p


def outro():
    img = scrim(88, 178)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 8], fill=ACCENT + (235,))

    title = '记住三件事'
    tf = font(FONT_B, 96)
    tw = d.textlength(title, font=tf)
    d.text(((W - tw) / 2, 250), title, font=tf, fill=TEXT)

    lines = [
        ('师生差距', '别超过 20 倍'),
        ('数据覆盖', '比数量更重要'),
        ('许可证', '先查再动手'),
    ]
    y = 430
    lf = font(FONT_R, 52)
    kf = font(FONT_B, 52)
    for k, v in lines:
        kw = d.textlength(k, font=kf)
        vw = d.textlength(v, font=lf)
        total = kw + 40 + vw
        x = (W - total) / 2
        d.text((x, y), k, font=kf, fill=ACCENT[:3] + (255,))
        d.text((x + kw + 40, y), v, font=lf, fill=TEXT)
        y += 96

    d.rectangle([(W - 700) / 2, y + 40, (W + 700) / 2, y + 42], fill=(90, 120, 170, 200))

    tail = '蒸馏是把大模型的能力，工程化地搬进小模型'
    tf2 = font(FONT_R, 40)
    t2w = d.textlength(tail, font=tf2)
    d.text(((W - t2w) / 2, y + 80), tail, font=tf2, fill=DIM)

    p = os.path.join(CARDS, 'outro.png')
    img.save(p)
    return p


if __name__ == '__main__':
    print('intro ->', intro())
    print('outro ->', outro())
