"""Per-phase medians of tools/gpu-memory-run.ps1 runs (spike: docs/perf/spike-direct-images.md).

    python tools/gpu-memory-summary.py "artifacts/poc-bench/mem-*"

Each run folder has the app's memory.csv (Godot's accounting, with the phase: browsing, running, returned) and gpu.csv
(Windows' GPU Process Memory counters). A gpu.csv sample takes the phase of the last app sample before it; samples in
the first 3 s after a phase change are skipped, so the medians are the settled state.
"""
import csv
import glob
import statistics
import sys
from datetime import datetime

SETTLE_S = 3.0
PHASES = ("browsing", "running", "returned")


def when(text):
    # .NET's round-trip format has 7 fractional digits; Python takes 6.
    head, _, frac = text.rstrip("Z").partition(".")
    return datetime.fromisoformat(f"{head}.{frac[:6].ljust(6, '0')}").timestamp()


def summarise(folder):
    app = [(when(r["utc"]), r) for r in csv.DictReader(open(f"{folder}/memory.csv", encoding="utf-8"))]
    gpu = [(when(r["utc"]), r) for r in csv.DictReader(open(f"{folder}/gpu.csv", encoding="utf-8"))]
    changes, last = [], None
    for t, r in app:
        if r["phase"] != last:
            changes.append((t, r["phase"]))
            last = r["phase"]

    def phase_at(t):
        current, since = None, None
        for at, phase in changes:
            if at <= t:
                current, since = phase, at
        return current, (t - since) if since is not None else 0

    rows = {}
    for phase in PHASES:
        a = [r for t, r in app if r["phase"] == phase and phase_at(t)[1] >= SETTLE_S]
        g = [r for t, r in gpu if phase_at(t)[0] == phase and phase_at(t)[1] >= SETTLE_S]
        if not a:
            continue
        med = lambda rs, k: statistics.median(float(r[k]) for r in rs) if rs else float("nan")
        rows[phase] = {
            "godot_video": med(a, "godot_video_mem_mb"),
            "godot_tex": med(a, "godot_texture_mem_mb"),
            "dedicated": med(g, "dedicated_mb"),
            "shared": med(g, "shared_mb"),
            "committed": med(g, "committed_mb"),
            "ws": med(a, "working_set_mb"),
            "private": med(a, "private_mb"),
            "n": len(g),
        }
    return rows


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else "artifacts/poc-bench/mem-*"
    print(f"{'run':<22} {'phase':<9} {'godot video':>11} {'godot tex':>9} {'gpu dedic.':>10} {'gpu shared':>10} {'gpu commit':>10} {'working set':>11} {'private':>8} {'n':>3}")
    for folder in sorted(glob.glob(pattern)):
        for phase, r in summarise(folder).items():
            print(f"{folder.replace(chr(92), '/').split('/')[-1]:<22} {phase:<9} {r['godot_video']:>11.1f} {r['godot_tex']:>9.1f} {r['dedicated']:>10.1f} "
                  f"{r['shared']:>10.1f} {r['committed']:>10.1f} {r['ws']:>11.1f} {r['private']:>8.1f} {r['n']:>3}")


if __name__ == "__main__":
    main()
