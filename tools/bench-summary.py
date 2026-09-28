"""Prints one line per run of each bench folder given (artifacts/bench/<timestamp>-<label>), for the perf docs.

    python tools/bench-summary.py artifacts/bench/*-final-scroll*
"""
import glob
import json
import os
import sys


def row(path):
    r = json.load(open(path, encoding='utf-8'))
    s = r.get('scroll')
    t = r.get('textures')
    m = r.get('memory') or {}
    parts = [
        f"our {r['app_startup_ms']:.0f} ms",
        f"{r['display']['window_width']}x{r['display']['window_height']} {r['display'].get('window_mode', '')}",
        f"scale {r.get('options', {}).get('render_scale', 1):.2f} {r.get('options', {}).get('upscaler', '')}",
        f"gpu {r['render_ms']['gpu_mean_ms']:.2f} ms",
    ]
    if s:
        f = s['frames']
        parts += [
            f"scroll {f['count']} frames: mean {f['mean_ms']:.2f} p99 {f['p99_ms']:.2f} max {f['max_ms']:.1f} ms",
            f"hitches {f['hitch_count']} over2x {f['over2x_count']}",
            f"textured {s['textured_fraction_mean'] * 100:.2f}% (min {s['textured_fraction_min'] * 100:.1f}%)",
            f"visible textured {s['visible_textured_ms'] if s['visible_textured_ms'] is not None else '-'} ms",
            f"main alloc {s['main_thread_allocated_bytes']} B",
            f"gc {s['gen0']}/{s['gen1']}/{s['gen2']}",
        ]
    else:
        f = r['frames']
        parts += [f"frames {f['count']}: mean {f['mean_ms']:.2f} p99 {f['p99_ms']:.2f} max {f['max_ms']:.1f} ms hitches {f['hitch_count']} over2x {f['over2x_count']}"]
    if t:
        parts += [f"uploads {t['uploads']} (cap hit {t['frames_at_count_cap']}, budget hit {t['frames_at_byte_budget']}) decode {t['decode_mean_ms']:.2f} ms"]
    if m:
        parts += [f"ws {m['working_set_bytes'] / 2**20:.0f} MB (peak {m['peak_working_set_bytes'] / 2**20:.0f}) tex {m['texture_mem_bytes'] / 2**20:.1f} MB"]
    return ' | '.join(parts)


for pattern in sys.argv[1:]:
    for folder in sorted(glob.glob(pattern)):
        print(os.path.basename(folder))
        for run in sorted(glob.glob(os.path.join(folder, 'run-*.json'))):
            if run.endswith('run-0.json'):
                continue
            print('  ' + os.path.basename(run)[:-5] + ': ' + row(run))
