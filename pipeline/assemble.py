"""Assemble the final video: intro card, 10 narrated segments, outro card.

Each narrated segment uses one H3 clip in slow motion with the paragraph overlay
burned in. Alternate segments get a slight punch-in so consecutive shots do not
look like the same camera.
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
CARDS = os.path.join(OUT, 'cards')
CLIPS = os.path.join(OUT, 'clips')
SEGS = os.path.join(OUT, 'segments')
FF = imageio_ffmpeg.get_ffmpeg_exe()

W, H = 1920, 1080
SLOW = 3.0
PUNCH = 1.10          # extra zoom on every other shot
INTRO_SECONDS = 2.4
OUTRO_SECONDS = 3.2

os.makedirs(SEGS, exist_ok=True)


def run(args):
    r = subprocess.run(args, capture_output=True, text=True, errors='replace')
    if r.returncode != 0:
        print('FFMPEG FAILED:', ' '.join(args)[:160])
        print((r.stderr or '')[-700:])
        return False
    return True


def encode(seg, clip, overlay, dur, punch=False):
    zoom = PUNCH if punch else 1.0
    tw, th = int(W * zoom), int(H * zoom)
    vf = (
        f'[0:v]setpts=PTS*{SLOW},'
        f'scale={tw}:{th}:force_original_aspect_ratio=increase:flags=lanczos,'
        f'crop={W}:{H}[bg];'
        f'[bg][1:v]overlay=0:0[v]'
    )
    cmd = [FF, '-y', '-stream_loop', '-1', '-i', clip,
           '-loop', '1', '-i', overlay,
           '-filter_complex', vf,
           '-map', '[v]',
           '-t', f'{dur:.3f}', '-an',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
           '-pix_fmt', 'yuv420p', '-r', '24',
           seg]
    return run(cmd)


def main():
    manifest = json.load(io.open(os.path.join(TT, 'manifest.json'), encoding='utf-8'))
    items = manifest['items']
    all_clips = sorted(glob.glob(os.path.join(CLIPS, 'clip_*.webm')))

    wanted = [a.strip() for a in sys.argv[1:] if a.strip()]
    if wanted:
        clips = [c for c in all_clips
                 if os.path.splitext(os.path.basename(c))[0][5:] in wanted]
    else:
        clips = all_clips
    if not clips:
        print('no clips found in', CLIPS)
        sys.exit(1)
    print(f'{len(clips)} clip(s): {[os.path.basename(c) for c in clips]}')

    seg_paths = []

    def pick(name, fallback):
        for c in clips:
            if os.path.basename(c) == f'clip_{name}.webm':
                return c
        return fallback

    # --- intro card ---
    if os.path.exists(os.path.join(CARDS, 'intro.png')):
        seg = os.path.join(SEGS, 'seg00.mp4')
        if encode(seg, pick('g2', clips[0]), os.path.join(CARDS, 'intro.png'),
                  INTRO_SECONDS, None):
            seg_paths.append(seg)
            print(f'  intro  {INTRO_SECONDS:4.1f}s')

    # --- narrated paragraphs ---
    for i, item in enumerate(items):
        idx = item['index']
        clip = clips[i % len(clips)]
        overlay = os.path.join(OV, f'ov{idx:02d}.png')
        wav = os.path.join(TT, f'p{idx:02d}.wav')
        seg = os.path.join(SEGS, f'seg{idx:02d}.mp4')
        if not (os.path.exists(overlay) and os.path.exists(wav)):
            print(f'  seg{idx:02d} missing inputs')
            continue
        ok = encode(seg, clip, overlay, item['seconds'], punch=(i % 2 == 1))
        print(f'  seg{idx:02d} {item["seconds"]:5.1f}s {os.path.basename(clip)}'
              f'{" [punch]" if i % 2 else ""} -> {"ok" if ok else "FAIL"}')
        if ok:
            seg_paths.append(seg)

    # --- outro card ---
    if os.path.exists(os.path.join(CARDS, 'outro.png')):
        seg = os.path.join(SEGS, 'seg99.mp4')
        if encode(seg, pick('g4', clips[0]), os.path.join(CARDS, 'outro.png'), OUTRO_SECONDS):
            seg_paths.append(seg)
            print(f'  outro  {OUTRO_SECONDS:4.1f}s')

    if not seg_paths:
        print('no segments produced')
        sys.exit(1)

    list_path = os.path.join(SEGS, 'concat.txt')
    with io.open(list_path, 'w', encoding='utf-8') as fh:
        for p in seg_paths:
            fh.write(f"file '{p.replace(chr(92), '/')}'\n")

    silent = os.path.join(OUT, '_video_silent.mp4')
    ok = run([FF, '-y', '-f', 'concat', '-safe', '0', '-i', list_path,
              '-c', 'copy', silent])
    if not ok:
        sys.exit(1)

    final = os.path.join(OUT, 'distillation_explainer.mp4')
    audio_path = os.path.join(OUT, 'audio_final.wav')
    if os.path.exists(audio_path):
        ok = run([FF, '-y', '-i', silent, '-i', audio_path,
                  '-map', '0:v:0', '-map', '1:a:0',
                  '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
                  '-shortest', '-movflags', '+faststart', final])
        if ok and os.path.exists(silent):
            os.remove(silent)
    else:
        print('WARNING: audio_final.wav missing, output has no sound')
        os.replace(silent, final)
        ok = True

    print('FINAL:', final if ok else 'FAILED')
    if ok and os.path.exists(final):
        print(f'  {os.path.getsize(final)/1e6:.1f} MB')


if __name__ == '__main__':
    main()
