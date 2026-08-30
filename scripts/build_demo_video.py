#!/usr/bin/env python3
"""Assemble the 3-minute Track 4 walkthrough from real Agent output + cards.

Does not fake a desktop recording. Uses the frozen public_0002 transcript
and the same numbers as report/freeze.md. Writes:

    report/demo_video/bytesize_track4_demo.mp4
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "demo_video"
FRAMES = OUT / "_frames"
VIDEO = OUT / "bytesize_track4_demo.mp4"
SRT = OUT / "captions.en.srt"
W, H = 1920, 1080

BG = (11, 11, 12)
INK = (244, 241, 234)
MUTED = (163, 158, 148)
ACCENT = (254, 44, 85)
CARD = (22, 22, 23)
GREEN = (140, 210, 160)
YELLOW = (232, 196, 110)
RED = (254, 44, 85)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ("C:/Windows/Fonts/calibrib.ttf", "C:/Windows/Fonts/calibri.ttf")
        if bold
        else ("C:/Windows/Fonts/calibri.ttf",)
    )
    extra = ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf")
    for path in names + extra:
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def mono(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cascadiamono.ttf",
        "C:/Windows/Fonts/lucon.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return font(size)


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 18, H), fill=ACCENT)
    draw.text((48, 1018), "ByteSize  ·  Track 4  ·  TikTok TechJam 2026", font=font(22), fill=MUTED)
    return img, draw


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        words = para.split(" ")
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if draw.textlength(trial, font=fnt) <= width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


def save(img: Image.Image, name: str) -> Path:
    FRAMES.mkdir(parents=True, exist_ok=True)
    path = FRAMES / name
    img.save(path, "PNG")
    return path


def card_title() -> Path:
    img, draw = canvas()
    draw.text((56, 220), "TIKTOK TECHJAM 2026  ·  TRACK 4", font=font(26, True), fill=ACCENT)
    y = 300
    for line in (
        "Evidence-Aware Conversational Search",
        "with Value-of-Information Stopping",
    ):
        draw.text((56, y), line, font=font(52, True), fill=INK)
        y += 72
    draw.text((56, 520), "ByteSize  ·  ContestAgent PUBLIC  ·  0 tokens", font=font(30), fill=MUTED)
    return save(img, "01_title.png")


def card_claim() -> Path:
    img, draw = canvas()
    draw.text((56, 160), "THE CLAIM", font=font(26, True), fill=ACCENT)
    y = 240
    for line in wrap(
        draw,
        "We stopped optimizing how the agent ranks, and started optimizing when it knows enough to rank.",
        font(42, True),
        1760,
    ):
        draw.text((56, y), line, font=font(42, True), fill=INK)
        y += 62
    y += 24
    for line in wrap(
        draw,
        "Scoring taxes extra turns. E1/E2/E3 still ask — once — only when the expected value of the next other is higher than the MTTC cost.",
        font(28),
        1760,
    ):
        draw.text((56, y), line, font=font(28), fill=MUTED)
        y += 42
    return save(img, "02_claim.png")


def card_results() -> Path:
    img, draw = canvas()
    draw.text((56, 70), "800 UNSEEN SESSIONS  ·  8 ID-DISJOINT SHARDS", font=font(24, True), fill=ACCENT)
    boxes = [
        (56, "+60", "Rank-1 / 800"),
        (656, "8 / 8", "shards improved"),
        (1256, "0", "Hit-rate loss"),
    ]
    for x, n, label in boxes:
        draw.rounded_rectangle((x, 140, x + 560, 360), radius=12, fill=CARD)
        cx = x + 280
        draw.text((cx, 230), n, font=font(72, True), fill=INK, anchor="mm")
        draw.text((cx, 310), label, font=font(26), fill=MUTED, anchor="mm")

    rows = [
        ("Split", "Hit@10", "MRR", "Score", "Rank-1"),
        ("Public 200", "1.000", "0.954167", "0.95125", "184"),
        ("Holdout 200", "0.980", "0.864845", "0.911753", "162"),
    ]
    cols = [56, 420, 760, 1120, 1480]
    y0 = 420
    draw.rounded_rectangle((56, y0, 1864, 700), radius=12, fill=CARD)
    for r, row in enumerate(rows):
        yy = y0 + 40 + r * 80
        color = MUTED if r == 0 else INK
        f = font(26, True) if r == 0 or r == 1 else font(26)
        for c, cell in enumerate(row):
            draw.text((cols[c], yy), cell, font=f, fill=color)
    return save(img, "03_results.png")


def card_close() -> Path:
    img, draw = canvas()
    draw.text((56, 180), "SCORED PATH", font=font(26, True), fill=ACCENT)
    draw.text((56, 250), "starter.agent.Agent  →  ContestAgent PUBLIC", font=font(36, True), fill=INK)
    draw.text((56, 320), "progress_defer = e123   ·   MiniLM late fusion   ·   0 LLM tokens", font=font(28), fill=MUTED)
    draw.rounded_rectangle((56, 420, 1500, 520), radius=8, fill=CARD)
    draw.text((80, 448), "python -m evaluator.local_evaluator", font=mono(28), fill=INK)
    draw.text((56, 580), "ByteSize  ·  contest/public  ·  reproducible locally", font=font(26), fill=MUTED)
    draw.text((56, 640), "Always ask other. Verbatim AND. Do not rank until the evidence is enough.", font=font(26), fill=MUTED)
    return save(img, "04_close.png")


def term_frame(title: str, body: list[str], caption: str) -> Image.Image:
    img, draw = canvas()
    draw.text((56, 48), "LIVE  ·  official simulator  ·  public_0002", font=font(22, True), fill=ACCENT)
    draw.text((56, 88), title, font=font(32, True), fill=INK)
    draw.rounded_rectangle((56, 150, 1864, 900), radius=12, fill=(16, 16, 18))
    y = 176
    fnt = mono(26)
    for line in body:
        color = INK
        if line.startswith("customer:"):
            color = YELLOW
        elif line.startswith("agent:"):
            color = GREEN
        elif "<= TARGET" in line or line.startswith("HIT"):
            color = ACCENT
        elif line.startswith("ask=") or line.startswith("usage") or line.startswith("["):
            color = MUTED
        draw.text((88, y), line[:110], font=fnt, fill=color)
        y += 36
        if y > 860:
            break
    draw.text((56, 930), caption, font=font(24), fill=MUTED)
    return img


def terminal_scenes() -> list[tuple[Path, float]]:
    scenes: list[tuple[Path, float]] = []

    def put(name: str, title: str, body: list[str], caption: str, seconds: float) -> None:
        img = term_frame(title, body, caption)
        scenes.append((save(img, name), seconds))

    put(
        "t0_header.png",
        "Intent Override  ·  0 tokens",
        [
            "scenario=intent_override   sample=public_0002",
            "target=B071X54486  Hide & Drink leather belt",
            "ask_attribute is always other. Ranking waits for evidence.",
        ],
        "Same evaluator the organizers ship. No website.",
        10,
    )
    put(
        "t1.png",
        "Turn 1  ·  withhold",
        [
            "customer: I'm looking for Accessories Belts. Buckle closure",
            "agent:    Matching Accessories Belts — buckle closure.",
            "          What material or fabric should I match?",
            "ask=other  pool=258  hard=111  withhold=True  usage=0",
        ],
        "Pool is still large. Do not dump a ranked list yet.",
        17,
    )
    put(
        "t2.png",
        "Turn 2  ·  still gathering",
        [
            "customer: For that, what matters is: leather; 100% Leather.",
            "agent:    Matching Accessories Belts — leather; 100% leather.",
            "          Any colour or print I should lock in?",
            "ask=other  pool=258  hard=22  withhold=True  usage=0",
        ],
        "Hard pool 258 → 22. One more question is still worth the MTTC tax.",
        17,
    )
    put(
        "t3.png",
        "Turn 3  ·  override replaces state",
        [
            "[simulator] intent override",
            "customer: Actually, ignore my earlier preference. What I need is: leather.",
            "agent:    I'll follow the updated requirement.",
            "scope=referenced_preference_replace  withhold=True  usage=0",
        ],
        "Slots are replaced, not appended. Hits before override cannot score.",
        18,
    )
    put(
        "t4.png",
        "Turn 4  ·  evidence is enough",
        [
            "customer: For that, what matters is: Imported; Buckle closure.",
            "agent:    Here are the closest matches so far.",
            "ask=other  hard=7  withhold=False  usage=0",
            "  1. B071X54486  Hide & Drink Full Grain Leather Men's Belt  <= TARGET",
            "  2. B072M9PJ3H  find. Men's Leather Formal Belt",
            "  3. B016B07WZI  Dona Michi MEN'S WORK BELT",
        ],
        "Recommend now. Target is rank 1.",
        25,
    )
    put(
        "t5_hit.png",
        "HIT  ·  turn 4  ·  rank 1",
        [
            "--- outcome ---",
            "HIT turn=4 rank=1",
            "tokens prompt=0 completion=0",
        ],
        "Value-of-information stop: ask while the answer changes ranking; stop when it does not.",
        8,
    )
    return scenes


def find_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise SystemExit("ffmpeg not found. pip install imageio-ffmpeg")


def concat(ffmpeg: str, clips: list[tuple[Path, float]], dest: Path) -> None:
    list_path = FRAMES / "concat.txt"
    lines = []
    for path, seconds in clips:
        lines.append(f"file '{path.as_posix()}'")
        lines.append(f"duration {seconds:.3f}")
    lines.append(f"file '{clips[-1][0].as_posix()}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    raw = FRAMES / "raw.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-vf",
            "fps=30,format=yuv420p",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(raw),
        ],
        check=True,
    )
    # Burn English captions if ffmpeg has the subtitles filter (libass).
    burned = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(raw),
            "-vf",
            f"subtitles={SRT.as_posix()}:force_style='FontName=Calibri,FontSize=18,PrimaryColour=&H00EAF1F4,OutlineColour=&H00160B0B,Outline=2'",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(dest),
        ],
        capture_output=True,
        text=True,
    )
    source = dest if burned.returncode == 0 else raw
    if burned.returncode != 0:
        print("captions not burned (no libass); upload captions.en.srt on YouTube", file=sys.stderr)
        print(burned.stderr[-800:], file=sys.stderr)
    trimmed = FRAMES / "trimmed.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-t",
            "180",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(trimmed),
        ],
        check=True,
    )
    shutil.copyfile(trimmed, dest)
    print(f"wrote {dest}  ({dest.stat().st_size} bytes)")


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    clips: list[tuple[Path, float]] = [
        (card_title(), 18),
        (card_claim(), 20),
        *terminal_scenes(),
        (card_results(), 25),
        (card_close(), 22),
    ]
    total = sum(s for _, s in clips)
    print(f"timeline {total:.1f}s  clips={len(clips)}")
    ffmpeg = find_ffmpeg()
    concat(ffmpeg, clips, VIDEO)


if __name__ == "__main__":
    main()
