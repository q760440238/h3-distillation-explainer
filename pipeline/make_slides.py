"""Render the 1920x1080 slide set for the distillation explainer.

One slide per narration paragraph. Text is composited with Pillow so Chinese
typography is deterministic (generated images cannot be trusted with text).
"""

import io
import json
import os
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = r'E:\minimaxh3\out'
SLIDES = os.path.join(OUT, 'slides')
PHOTO = r'E:\minimaxh3\帅气照片.jpg'
FONT_B = r'C:\Windows\Fonts\msyhbd.ttc'
FONT_R = r'C:\Windows\Fonts\msyh.ttc'

W, H = 1920, 1080
os.makedirs(SLIDES, exist_ok=True)

# headline + bullets per paragraph (index 1..10)
CONTENT = [
    ('为什么 7B 能打 70B？', ['答案就是蒸馏', '把大模型的能力，搬进小模型']),
    ('为什么要蒸馏', ['大模型很强，但太贵', '小模型想干大模型的活', '这是最划算的一条路']),
    ('蒸馏的本质', ['不只学老师的答案', '还学老师的思考方式', '软标签比标准答案信息量更大']),
    ('方法一 · Logit 蒸馏', ['拟合老师的概率分布', '温度调高，挖出暗知识', '"猫更像狗，而不是汽车"', '分类和 CV 最常用']),
    ('方法二 · 特征蒸馏', ['搬老师的中间层和注意力图', 'TinyBERT：4 层达到 96%', '体积只有老师的 1/7.5']),
    ('方法三 · On-Policy 蒸馏', ['学生自己写，老师逐 token 打分', 'MiniLLM / GKD / Qwen3 都用', '配长思维链 = R1 的做法', '当前 LLM 蒸馏的主流']),
    ('工业实践 · 强到弱三阶段', ['SFT 打底', 'logits + on-policy 精修', '专项强化', 'Gemma 2 的 2B / 9B 就这么来']),
    ('落地路线 · 五步', ['选教师 → 造数据 → 做 SFT → 精修 → 量化部署', '数据宁可少而精', '先蒸馏，再量化，顺序别反']),
    ('提升有多大', ['CV 小模型：掉点不到 1 个点', 'BERT 类：掉 3–4 个点', '通用 7B：到老师九成', '推理 7B：85%–95%，要看 pass@k']),
    ('三个提醒', ['师生差距别超过 20 倍', '数据覆盖比数量重要', '许可证和 API 条款，先查再动手']),
]


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_w):
    """Greedy wrap that works for CJK (no spaces) and latin alike."""
    lines, cur = [], ''
    for ch in text:
        trial = cur + ch
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def background(idx):
    """Vertical gradient with a soft accent glow, unique-ish per slide."""
    top = (14, 18, 28)
    bottom = (26, 34, 52)
    img = Image.new('RGB', (W, H), top)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=(int(top[0] + (bottom[0] - top[0]) * t),
                     int(top[1] + (bottom[1] - top[1]) * t),
                     int(top[2] + (bottom[2] - top[2]) * t)))
    glow = Image.new('RGB', (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx = 260 + (idx % 3) * 620
    gd.ellipse([cx - 520, -320, cx + 520, 620], fill=(40, 90, 180))
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    img = Image.blend(img, Image.new('RGB', (W, H), (0, 0, 0)), 0.0)
    return Image.blend(img, glow, 0.22)


def teacher_portrait(size=300):
    """Circular crop of the reference photo, subtle rim."""
    src = Image.open(PHOTO).convert('RGB')
    side = min(src.size)
    left = (src.width - side) // 2
    top = (src.height - side) // 3
    src = src.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)

    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    ring = Image.new('RGB', (size + 16, size + 16), (0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse([0, 0, size + 15, size + 15], outline=(110, 160, 235), width=5)

    out = Image.new('RGBA', (size + 16, size + 16), (0, 0, 0, 0))
    out.paste(src, (8, 8), mask)
    out.alpha_composite(ring.convert('RGBA').crop((0, 0, size + 16, size + 16)))
    # keep only the ring outline: re-draw over transparency
    out = Image.new('RGBA', (size + 16, size + 16), (0, 0, 0, 0))
    out.paste(src, (8, 8), mask)
    rd2 = ImageDraw.Draw(out)
    rd2.ellipse([2, 2, size + 13, size + 13], outline=(110, 160, 235, 220), width=5)
    return out


def render(idx, title, bullets, paragraph, total):
    img = background(idx)
    d = ImageDraw.Draw(img)

    # left accent bar
    d.rectangle([0, 0, 10, H], fill=(90, 150, 240))
    d.rectangle([0, 0, 10, int(H * idx / total)], fill=(140, 200, 255))

    # slide counter
    d.text((96, 70), f'{idx:02d} / {total:02d}', font=font(FONT_R, 34), fill=(120, 138, 168))

    # title
    d.text((96, 148), title, font=font(FONT_B, 92), fill=(240, 246, 255))

    # underline
    tw = d.textlength(title, font=font(FONT_B, 92))
    d.rectangle([96, 268, 96 + tw, 274], fill=(90, 150, 240))

    # bullets
    y = 330
    bf = font(FONT_R, 46)
    for b in bullets:
        d.ellipse([100, y + 18, 122, y + 40], fill=(90, 150, 240))
        for line in wrap(d, b, bf, W - 620):
            d.text((150, y), line, font=bf, fill=(220, 230, 245))
            y += 62
        y += 24

    # teacher portrait, top right
    portrait = teacher_portrait(300)
    img.paste(portrait, (W - 400, 90), portrait)
    d.text((W - 400, 420), '讲解 · Distillation', font=font(FONT_R, 30), fill=(130, 150, 180))

    # subtitle band with this paragraph's narration
    band_h = 132
    d.rectangle([0, H - band_h, W, H], fill=(8, 10, 16))
    d.rectangle([0, H - band_h, W, H - band_h + 3], fill=(90, 150, 240))
    sfont = font(FONT_R, 36)
    lines = wrap(d, paragraph, sfont, W - 192)
    ty = H - band_h + 20
    for line in lines[:2]:
        d.text((96, ty), line, font=sfont, fill=(200, 212, 232))
        ty += 48

    path = os.path.join(SLIDES, f'slide{idx:02d}.png')
    img.save(path, quality=95)
    return path


def main():
    manifest = json.load(io.open(os.path.join(OUT, 'tts', 'manifest.json'), encoding='utf-8'))
    items = manifest['items']
    total = len(items)
    paths = []
    for item in items:
        idx = item['index']
        title, bullets = CONTENT[idx - 1]
        p = render(idx, title, bullets, item['text'], total)
        paths.append({'png': p, 'seconds': item['seconds'], 'text': item['text']})
        print(f'  slide{idx:02d} {item["seconds"]:5.1f}s  {title}')
    with io.open(os.path.join(OUT, 'slides.json'), 'w', encoding='utf-8') as fh:
        json.dump(paths, fh, ensure_ascii=False, indent=1)
    print(f'\n共 {len(paths)} 张，总时长 {sum(p["seconds"] for p in paths):.1f} 秒')


if __name__ == '__main__':
    main()
