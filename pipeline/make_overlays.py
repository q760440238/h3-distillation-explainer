"""Render transparent overlays (1920x1080 RGBA) for the H3 video.

One overlay per narration paragraph. Everything is drawn on the left of the
frame so the generated teacher (centre-right) stays visible, and the bottom
band carries the spoken sentence as a subtitle.
"""

import io
import json
import os

from PIL import Image, ImageDraw, ImageFont

OUT = r'E:\minimaxh3\out'
OVER = os.path.join(OUT, 'overlays')
FONT_B = r'C:\Windows\Fonts\msyhbd.ttc'
FONT_R = r'C:\Windows\Fonts\msyh.ttc'

W, H = 1920, 1080
os.makedirs(OVER, exist_ok=True)

CONTENT = [
    ('为什么 7B 能打 70B？', ['答案就是蒸馏', '把大模型的能力，工程化搬进小模型']),
    ('为什么要蒸馏', ['大模型很强，但太贵', '小模型想干大模型的活', '这是最划算的一条路']),
    ('蒸馏的本质', ['不只学老师的答案', '还学老师的思考方式', '软标签比标准答案信息量更大']),
    ('方法一 · Logit 蒸馏', ['拟合老师的概率分布', '温度调高，挖出暗知识', '"猫更像狗，而不是汽车"', '分类和 CV 最常用']),
    ('方法二 · 特征蒸馏', ['搬老师的中间层和注意力图', 'TinyBERT：4 层达到 96%', '体积只有老师的 1/7.5']),
    ('方法三 · On-Policy 蒸馏', ['学生自己写，老师逐 token 打分', 'MiniLLM / GKD / Qwen3 都用', '配长思维链 = R1 的做法']),
    ('工业实践 · 强到弱三阶段', ['SFT 打底', 'logits + on-policy 精修', '专项强化', 'Gemma 2 的 2B / 9B']),
    ('落地路线 · 五步', ['选教师 → 造数据 → SFT', '精修 → 量化部署', '先蒸馏，再量化']),
    ('提升有多大', ['CV 小模型：掉点 < 1 个点', 'BERT 类：掉 3–4 个点', '通用 7B：到老师九成', '推理 7B：85%–95%，看 pass@k']),
    ('三个提醒', ['师生差距 ≤ 20 倍', '数据覆盖 > 数量', '许可证先查再动手']),
]

ACCENT = (96, 170, 255)
TEXT = (232, 240, 255)
DIM = (150, 172, 205)

# paragraph index -> (section colour, section label)
SECTIONS = {
    1: ((110, 170, 255), '开篇'),
    2: ((110, 170, 255), '开篇'),
    3: ((110, 170, 255), '开篇'),
    4: ((69, 224, 200), '三套做法'),
    5: ((69, 224, 200), '三套做法'),
    6: ((69, 224, 200), '三套做法'),
    7: ((167, 139, 250), '工业实践'),
    8: ((167, 139, 250), '工业实践'),
    9: ((255, 184, 110), '效果与提醒'),
    10: ((255, 184, 110), '效果与提醒'),
}


def font(path, size):
    return ImageFont.truetype(path, size)


import re

BREAK_AFTER = '，。、；：）」』!?！？,.;:'
LATIN_WORD = re.compile(r'[A-Za-z0-9][A-Za-z0-9%\.\+\-/]*')
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')


def _tokenize(text):
    """Split into units that must not be broken: latin words stay whole,
    CJK chars and punctuation go one by one."""
    tokens, i = [], 0
    while i < len(text):
        m = LATIN_WORD.match(text, i)
        if m:
            tokens.append(m.group(0))
            i = m.end()
            continue
        ch = text[i]
        if ch.isspace():
            tokens.append(' ')
        else:
            tokens.append(ch)
        i += 1
    return tokens


def _greedy_tokens(draw, tokens, fnt, max_w):
    lines, cur, cur_w = [], [], 0.0
    for tok in tokens:
        w = draw.textlength(tok, font=fnt)
        if cur_w + w <= max_w or not cur:
            cur.append(tok)
            cur_w += w
        else:
            lines.append(cur)
            cur = [] if tok == ' ' else [tok]
            cur_w = 0.0 if tok == ' ' else w
    if cur:
        lines.append(cur)
    return lines


def _join(tokens):
    return ''.join(tokens).strip()


def wrap(draw, text, fnt, max_w, min_tail=3):
    """CJK-friendly wrap: latin words stay whole, no one-character last line."""
    lines = _greedy_tokens(draw, _tokenize(text), fnt, max_w)
    if len(lines) <= 1:
        return [_join(lines[0])] if lines else ['']

    # move whole tokens back so the last line is not a lonely character
    guard = 0
    while (len(lines) >= 2 and len(_join(lines[-1])) < min_tail
           and len(lines[-2]) > 2 and guard < 6):
        guard += 1
        cand = lines[-2][-1]
        if draw.textlength(cand + _join(lines[-1]), font=fnt) > max_w:
            break
        lines[-1].insert(0, lines[-2].pop())

    # prefer breaking right after punctuation when the next unit is CJK
    for i in range(len(lines) - 1):
        nxt = _join(lines[i + 1])
        if nxt and CJK.match(nxt[0]):
            for k in range(len(lines[i]) - 1, max(1, len(lines[i]) - 6), -1):
                if lines[i][k - 1] and lines[i][k - 1][-1] in BREAK_AFTER:
                    moved = lines[i][k:]
                    if draw.textlength(''.join(moved) + nxt, font=fnt) <= max_w:
                        lines[i + 1] = moved + lines[i + 1]
                        del lines[i][k:]
                    break
    return [_join(toks) for toks in lines if _join(toks)]



def rounded(draw, box, radius, fill, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def render(idx, total, title, bullets, paragraph, progress=0.0):
    colour, section = SECTIONS.get(idx, (ACCENT, ''))
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # --- top progress bar ---
    d.rectangle([0, 0, W, 6], fill=(255, 255, 255, 26))
    d.rectangle([0, 0, int(W * progress), 6], fill=colour + (235,))

    card_x0, card_x1 = 80, 720
    card_y0, card_y1 = 250, 820
    pad_x = 36

    # title shrinks until it fits inside the card
    title_size = 62
    while title_size > 40:
        tf = font(FONT_B, title_size)
        if d.textlength(title, font=tf) <= (card_x1 - card_x0) - 2 * pad_x:
            break
        title_size -= 2
    tf = font(FONT_B, title_size)

    bf = font(FONT_R, 38)
    bullet_lines = [wrap(d, b, bf, card_x1 - card_x0 - 2 * pad_x - 44) for b in bullets]

    # card grows with its content instead of using a fixed height
    title_h = title_size + 26
    body_h = sum(len(ls) * 50 + 18 for ls in bullet_lines) + 34
    tabs_h = 78 if idx in (4, 5, 6) else 0
    content_h = 62 + title_h + body_h + tabs_h
    card_y1 = max(520, min(960, card_y0 + content_h))

    rounded(d, (card_x0, card_y0, card_x1, card_y1), 22,
            (10, 20, 38, 192), colour + (150,), 2)
    d.rectangle([card_x0, card_y0, card_x1, card_y0 + 6], fill=colour + (235,))

    # section chip + counter
    chip_w = d.textlength(section, font=font(FONT_R, 26)) + 28 if section else 0
    if section:
        rounded(d, (card_x0 + pad_x, card_y0 + 26, card_x0 + pad_x + chip_w, card_y0 + 68),
                14, colour + (46,), colour + (170,), 1)
        d.text((card_x0 + pad_x + 14, card_y0 + 33), section,
               font=font(FONT_R, 26), fill=colour + (255,))
    d.text((card_x0 + pad_x + chip_w + 16, card_y0 + 34), f'{idx:02d} / {total:02d}',
           font=font(FONT_R, 26), fill=DIM)
    d.text((card_x0 + pad_x, card_y0 + 84), title, font=tf, fill=TEXT)

    y = card_y0 + 84 + title_h + 18
    for lines in bullet_lines:
        d.ellipse([card_x0 + pad_x + 4, y + 14, card_x0 + pad_x + 22, y + 32], fill=colour + (255,))
        for line in lines:
            d.text((card_x0 + pad_x + 44, y), line, font=bf, fill=TEXT)
            y += 50
        y += 18

    # --- method tabs on the three "how" slides ---
    if idx in (4, 5, 6):
        y += 6
        d.rectangle([card_x0 + pad_x, y - 4, card_x1 - pad_x, y - 2], fill=(255, 255, 255, 26))
        tab_f = font(FONT_R, 24)
        labels = ['① Logit', '② 特征', '③ On-Policy']
        x = card_x0 + pad_x
        for k, name in enumerate(labels):
            tw = d.textlength(name, font=tab_f) + 30
            active = (k == idx - 4)
            if active:
                rounded(d, (x, y + 14, x + tw, y + 58), 12,
                        (8, 16, 30, 235), colour + (235,), 2)
                d.text((x + 15, y + 24), name, font=tab_f, fill=(255, 255, 255, 250))
            else:
                rounded(d, (x, y + 14, x + tw, y + 58), 12,
                        (255, 255, 255, 12), (120, 138, 168, 110), 1)
                d.text((x + 15, y + 24), name, font=tab_f, fill=(150, 168, 196, 220))
            x += tw + 12

    # --- top-right label ---
    label = '蒸馏 · DISTILLATION'
    lf = font(FONT_R, 28)
    lw = d.textlength(label, font=lf)
    d.text((W - 90 - lw, 60), label, font=lf, fill=(210, 225, 250, 220))

    # --- subtitle band ---
    band_top = 950
    for i in range(band_top, H):
        alpha = int(200 * (i - band_top) / (H - band_top))
        d.line([(0, i), (W, i)], fill=(6, 10, 18, alpha))
    d.rectangle([0, band_top, W, band_top + 3], fill=colour + (210,))

    sfont = font(FONT_R, 34)
    lines = wrap(d, paragraph, sfont, W - 200)
    ty = band_top + 22
    for line in lines[:2]:
        d.text((100, ty), line, font=sfont, fill=(206, 218, 238, 240))
        ty += 44

    path = os.path.join(OVER, f'ov{idx:02d}.png')
    img.save(path)
    return path


def main():
    manifest = json.load(io.open(os.path.join(OUT, 'tts', 'manifest.json'), encoding='utf-8'))
    items = manifest['items']
    total = len(items)
    out = []
    for item in items:
        idx = item['index']
        title, bullets = CONTENT[idx - 1]
        p = render(idx, total, title, bullets, item['text'])
        out.append({'index': idx, 'overlay': p, 'seconds': item['seconds']})
        print(f'  overlay{idx:02d}  {item["seconds"]:5.1f}s  {title}')
    json.dump(out, io.open(os.path.join(OUT, 'overlays.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'\n共 {len(out)} 张叠加层')


if __name__ == '__main__':
    main()
