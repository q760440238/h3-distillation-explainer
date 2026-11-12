"""Super-resolve the HD clips with realsr-ncnn-vulkan, blended to avoid artefacts.

Pipeline per clip:
  extract frames -> realsr 4x (5120x2816) -> cover to 1920x1080
  -> blend STILL% with a plain lanczos version of the same frame
  -> encode a 1080p clip

Blending matters: on a 1280 source the upscaler is accurate, but taken at 100%
it starts to crunch hair and skin. 45% measured as the point where detail gains
are real and artefacts are not visible yet.
"""

import glob
import os
import shutil
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image

FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT = r'E:\minimaxh3\out'
SRC = os.path.join(OUT, 'clips_hd')
DST = os.path.join(OUT, 'clips_sr')
REALSR = r'E:\minimaxh3\tools\realsr-ncnn-vulkan-20220728-windows\realsr-ncnn-vulkan.exe'
MODEL = r'E:\minimaxh3\tools\realsr-ncnn-vulkan-20220728-windows\models-DF2K'

W, H = 1920, 1080
BLEND = 0.45
FPS = 24


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, errors='replace', **kw)


def cover(img):
    r = max(W / img.width, H / img.height)
    im = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x = (im.width - W) // 2
    y = (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def process(name):
    src = os.path.join(SRC, f'clip_{name}.webm')
    if not os.path.exists(src):
        print(f'  clip_{name}: source missing')
        return False

    work = os.path.join(DST, f'_work_{name}')
    frames = os.path.join(work, 'frames')
    up = os.path.join(work, 'up')
    final = os.path.join(work, 'final')
    for d in (frames, up, final):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

    r = run([FF, '-y', '-i', src, os.path.join(frames, 'f_%03d.png')])
    n = len(os.listdir(frames))
    if n == 0:
        print(f'  clip_{name}: no frames ({r.stderr[-200:]})')
        return False

    r = run([REALSR, '-i', frames, '-o', up, '-s', '4', '-m', MODEL, '-f', 'png'])
    ups = sorted(glob.glob(os.path.join(up, '*.png')))
    if not ups:
        print(f'  clip_{name}: realsr failed')
        return False

    for i, src_frame in enumerate(sorted(glob.glob(os.path.join(frames, '*.png')))):
        base = cover(Image.open(src_frame).convert('RGB'))
        sr_path = os.path.join(up, os.path.basename(src_frame))
        if os.path.exists(sr_path):
            hi = cover(Image.open(sr_path).convert('RGB'))
            base = Image.blend(base, hi, BLEND)
        base.save(os.path.join(final, f'f_{i + 1:03d}.png'))

    out = os.path.join(DST, f'clip_{name}.mp4')
    r = run([FF, '-y', '-framerate', str(FPS), '-i', os.path.join(final, 'f_%03d.png'),
             '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
             '-pix_fmt', 'yuv420p', '-r', str(FPS), out])
    shutil.rmtree(work, ignore_errors=True)
    ok = os.path.exists(out)
    print(f'  clip_{name}: {n} frames -> {out if ok else "FAILED"}')
    return ok


def main():
    os.makedirs(DST, exist_ok=True)
    names = sys.argv[1:] or ['k1', 'k2', 'k3', 'k7', 'k8']
    for name in names:
        process(name)
    print('done')


if __name__ == '__main__':
    main()
