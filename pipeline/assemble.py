"""Assemble the final video from H3 clips + overlays + narration.

Each paragraph becomes one segment: a slow-motion pass of an H3 clip (so the
teacher keeps moving at a natural pace) with the paragraph overlay burned in and
its narration attached. Segments are then concatenated.
"""

import glob
import io
import json
import os
import subprocess
import sys

import imageio_ffmpeg

OUT = r'E:\minimaxh3\out'
TT = os.path.join(OUT, 'tts')
OV = os.path.join(OUT, 'overlays')
CLIPS = os.path.join(OUT, 'clips')
SEGS = os.path.join(OUT, 'segments')
FF = imageio_ffmpeg.get_ffmpeg_exe()

W, H = 1920, 1080
SLOW = 3.0          # stretch each 2 s clip to ~6 s of gentle motion

os.makedirs(SEGS, exist_ok=True)


def run(args):
    r = subprocess.run(args, capture_output=True, text=True, errors='replace')
    if r.returncode != 0:
        print('FFMPEG FAILED:', ' '.join(args)[:200])
        print((r.stderr or '')[-800:])
        return False
    return True


def main():
    manifest = json.load(io.open(os.path.join(TT, 'manifest.json'), encoding='utf-8'))
    items = manifest['items']
    clips = sorted(glob.glob(os.path.join(CLIPS, 'clip_*.webm')))
    if not clips:
        print('no clips found in', CLIPS)
        sys.exit(1)
    print(f'{len(clips)} clip(s): {[os.path.basename(c) for c in clips]}')

    seg_paths = []
    for i, item in enumerate(items):
        idx = item['index']
        dur = item['seconds']
        clip = clips[i % len(clips)]
        overlay = os.path.join(OV, f'ov{idx:02d}.png')
        wav = os.path.join(TT, f'p{idx:02d}.wav')
        seg = os.path.join(SEGS, f'seg{idx:02d}.mp4')
        if not (os.path.exists(overlay) and os.path.exists(wav)):
            print(f'  seg{idx:02d} missing inputs')
            continue

        vf = (
            f'[0:v]setpts=PTS*{SLOW},scale={W}:{H}:force_original_aspect_ratio=increase,'
            f'crop={W}:{H},fps=24[bg];'
            f'[bg][1:v]overlay=0:0[v]'
        )
        cmd = [FF, '-y',
               '-stream_loop', '-1', '-i', clip,
               '-loop', '1', '-i', overlay,
               '-i', wav,
               '-filter_complex', vf,
               '-map', '[v]', '-map', '2:a',
               '-t', f'{dur:.3f}',
               '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
               '-pix_fmt', 'yuv420p', '-r', '24',
               '-c:a', 'aac', '-b:a', '160k', '-ar', '44100',
               '-shortest', seg]
        ok = run(cmd)
        print(f'  seg{idx:02d} {dur:5.1f}s {os.path.basename(clip)} -> {"ok" if ok else "FAIL"}')
        if ok:
            seg_paths.append(seg)

    if not seg_paths:
        print('no segments produced')
        sys.exit(1)

    list_path = os.path.join(SEGS, 'concat.txt')
    with io.open(list_path, 'w', encoding='utf-8') as fh:
        for p in seg_paths:
            fh.write(f"file '{p.replace(chr(92), '/')}'\n")

    final = os.path.join(OUT, 'distillation_explainer.mp4')
    ok = run([FF, '-y', '-f', 'concat', '-safe', '0', '-i', list_path,
              '-c', 'copy', final])
    print('FINAL:', final if ok else 'FAILED')
    if ok and os.path.exists(final):
        size = os.path.getsize(final) / 1e6
        print(f'  {size:.1f} MB')


if __name__ == '__main__':
    main()
