"""Collect CCTV-angle construction footage and keep only what is measurable.

download -> extract frames -> measure worker pixel height -> keep or reject.

Most public construction cameras are marketing time-lapses mounted so far away
that workers are 10px tall and no PPE model can ever see a helmet on them.
This rejects those automatically instead of us eyeballing thumbnails.

The gate is necessary, not sufficient: it counts people, it cannot tell a
hi-vis ironworker from a commuter on a station platform. Look at one annotated
frame before trusting a KEEP — three cameras passed here on pedestrians, glass
reflections, and a finished stadium's sidewalk.

Usage:
    backend/.venv/bin/python ml/collect_footage.py URL --name brown_danoff
    ... --dry-run          # measure, print, delete. Nothing is kept.
    ... --fps 2 --max-frames 400
    ... --frames-dir DIR   # measure frames already on disk
    ... --self-test        # no network, just checks the keep/reject rule
"""

from __future__ import annotations

import argparse
import shutil
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "datasets" / "webcam_raw"
# backend/.venv is the one with ultralytics+torch+cuda.
PERSON_MODEL = Path(__file__).resolve().parent.parent / "backend" / "yolov8n.pt"

# Workers must land in the CCTV band. Below 40px no helmet is resolvable; above
# ~150px the camera is a handheld/closeup and tells us nothing about the angle
# the product actually runs on.
MIN_MEDIAN_HEIGHT_PX = 40.0
MAX_MEDIAN_HEIGHT_PX = 150.0
MIN_FRAMES_WITH_PERSON = 0.30
PERSON_CONF = 0.25
# At the default 640 yolov8n misses most 40-80px workers: on the I-376 deck cam
# it found 300 people at 640 and 825 at 1280 in the same 300 frames. The gate is
# meant to ask "are there workers in this footage", not "what does a downscaled
# detector notice", so measure at 1280.
PERSON_IMGSZ = 1280


@dataclass
class Measurement:
    frames: int
    frames_with_person: int
    heights: list[float]

    @property
    def person_rate(self) -> float:
        return self.frames_with_person / self.frames if self.frames else 0.0

    @property
    def median_height(self) -> float:
        return statistics.median(self.heights) if self.heights else 0.0


def verdict(m: Measurement) -> tuple[bool, str]:
    """Keep only footage where workers are big enough and actually present."""
    if not m.frames:
        return False, "no frames extracted"
    if m.median_height < MIN_MEDIAN_HEIGHT_PX:
        return False, f"median person height {m.median_height:.0f}px < {MIN_MEDIAN_HEIGHT_PX:.0f}px"
    if m.median_height > MAX_MEDIAN_HEIGHT_PX:
        return False, f"median person height {m.median_height:.0f}px > {MAX_MEDIAN_HEIGHT_PX:.0f}px (not a CCTV angle)"
    if m.person_rate < MIN_FRAMES_WITH_PERSON:
        return False, f"only {m.person_rate*100:.0f}% of frames have a person < {MIN_FRAMES_WITH_PERSON*100:.0f}%"
    return True, "ok"


# YouTube 429s / "confirm you're not a bot" after a handful of parallel pulls.
# Browser cookies make it behave; set to "" to disable.
COOKIES_FROM_BROWSER = "chrome"


def _ytdlp(*args: str) -> list[str]:
    cmd = ["yt-dlp", "--no-playlist"]
    if COOKIES_FROM_BROWSER:
        cmd += ["--cookies-from-browser", COOKIES_FROM_BROWSER]
    return cmd + list(args)


def is_live(url: str) -> bool:
    r = subprocess.run(
        _ytdlp("--print", "%(live_status)s", url), capture_output=True, text=True,
    )
    if r.returncode != 0:
        # Guessing here silently means recording a live stream with a seek range,
        # which fails several minutes later for a reason that looks unrelated.
        raise SystemExit(f"yt-dlp cannot read {url}:\n{r.stderr.strip()[-500:]}")
    return "is_live" in r.stdout


def download(url: str, dest: Path, seconds: int | None) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "source.%(ext)s"
    cmd = _ytdlp(
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "-o", str(out),
        url,
    )
    if seconds:
        if is_live(url):
            # A live stream has no seekable timeline; record N wall-clock seconds.
            cmd[1:1] = ["--downloader", "ffmpeg",
                        "--downloader-args", f"ffmpeg_i:-t {seconds}"]
        else:
            cmd[1:1] = ["--download-sections", f"*0-{seconds}",
                        "--force-keyframes-at-cuts"]
    subprocess.run(cmd, check=True)
    files = [p for p in dest.glob("source.*") if p.suffix != ".part"]
    if not files:
        raise SystemExit(f"yt-dlp produced nothing in {dest}")
    return files[0]


def extract(video: Path, frames_dir: Path, fps: float, max_frames: int) -> int:
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(video),
         "-vf", f"fps={fps}", "-frames:v", str(max_frames), "-q:v", "2",
         str(frames_dir / "f_%04d.jpg")],
        check=True,
    )
    return len(list(frames_dir.glob("*.jpg")))


def measure(frames_dir: Path) -> Measurement:
    from ultralytics import YOLO  # slow import, only needed here

    model = YOLO(str(PERSON_MODEL))
    frames = sorted(frames_dir.glob("*.jpg"))
    heights: list[float] = []
    with_person = 0
    # ponytail: batches of 8 at imgsz 1280 fit next to a training run on the same
    # GPU. Raise it if this ever has the card to itself and feels slow.
    for i in range(0, len(frames), 8):
        batch = [str(p) for p in frames[i:i + 8]]
        for r in model(batch, classes=[0], conf=PERSON_CONF, imgsz=PERSON_IMGSZ,
                       verbose=False):
            hs = [float(b.xyxy[0][3] - b.xyxy[0][1]) for b in r.boxes]
            if hs:
                with_person += 1
                heights.extend(hs)
    return Measurement(len(frames), with_person, heights)


def report(name: str, m: Measurement) -> None:
    print(f"\n=== {name} ===")
    print(f"frames            : {m.frames}")
    print(f"frames w/ person  : {m.frames_with_person} ({m.person_rate*100:.0f}%)")
    print(f"person detections : {len(m.heights)}")
    if m.heights:
        q = statistics.quantiles(m.heights, n=4) if len(m.heights) > 3 else [0, 0, 0]
        print(f"height px         : median {m.median_height:.0f}  "
              f"p25 {q[0]:.0f}  p75 {q[2]:.0f}  min {min(m.heights):.0f}  max {max(m.heights):.0f}")


def self_test() -> None:
    assert verdict(Measurement(0, 0, []))[0] is False
    assert verdict(Measurement(100, 90, [60.0] * 90))[0] is True
    assert verdict(Measurement(100, 90, [20.0] * 90))[0] is False  # too small
    assert verdict(Measurement(100, 90, [400.0] * 90))[0] is False  # too close
    assert verdict(Measurement(100, 10, [60.0] * 10))[0] is False  # too rare
    print("self-test ok")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("url", nargs="?", help="Video URL (anything yt-dlp handles)")
    p.add_argument("--name", help="Site subdirectory under datasets/webcam_raw/")
    p.add_argument("--fps", type=float, default=1.0)
    p.add_argument("--max-frames", type=int, default=300)
    p.add_argument("--seconds", type=int, default=900, help="Download only the first N seconds (0 = all)")
    p.add_argument("--dry-run", action="store_true", help="Measure then delete, keep nothing")
    p.add_argument("--frames-dir", type=Path, help="Skip download/extract, measure this dir")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()

    if args.self_test:
        return self_test()

    if args.frames_dir:
        m = measure(args.frames_dir)
        report(args.frames_dir.name, m)
        keep, why = verdict(m)
        print(f"verdict           : {'KEEP' if keep else 'REJECT'} ({why})")
        return

    if not args.url or not args.name:
        raise SystemExit("need URL and --name (or --frames-dir / --self-test)")

    site = ROOT / args.name
    video = download(args.url, site, args.seconds or None)
    n = extract(video, site / "frames", args.fps, args.max_frames)
    print(f"extracted {n} frames")
    m = measure(site / "frames")
    report(args.name, m)
    keep, why = verdict(m)
    print(f"source            : {args.url}")
    print(f"verdict           : {'KEEP' if keep else 'REJECT'} ({why})")

    if args.dry_run or not keep:
        shutil.rmtree(site)
        print(f"deleted {site}")
    else:
        video.unlink()  # frames are what we need; the mkv is 10-100x bigger
        (site / "SOURCE.txt").write_text(
            f"{args.url}\nfps={args.fps} frames={m.frames} "
            f"median_h={m.median_height:.0f}px person_rate={m.person_rate*100:.0f}%\n"
        )
        print(f"kept {site / 'frames'}")


if __name__ == "__main__":
    main()
