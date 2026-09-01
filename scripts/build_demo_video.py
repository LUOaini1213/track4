#!/usr/bin/env python3
"""Assemble the narrated 3-minute Track 4 walkthrough from real Agent output.

Does not fake a desktop recording. Uses the frozen public_0002 transcript and
the same numbers as report/freeze.md.

Storyboard (targets; a segment stretches if its narration needs longer):

    0:00-0:15  Problem        why conversational shopping fails today
    0:15-0:35  Our Solution   value-of-information stopping, in one line
    0:35-0:55  Architecture   five deterministic stages
    0:55-2:20  Live Demo      public_0002 end to end, turn by turn
    2:20-2:45  Results        metrics vs the weak baseline, 800-session study
    2:45-3:00  Impact         scale, privacy, portability

Narration is synthesised first, so slide durations and captions are derived
from the real audio length and cannot drift out of sync.

Voice-over tiers, each falling back to the next:

    edge-tts neural voice  ->  Windows SAPI (offline)  ->  silent video

Writes report/demo_video/bytesize_track4_demo.mp4 and captions.en.srt. The
existing MP4 is only replaced once the new render succeeds.

    python -m pip install edge-tts pillow imageio-ffmpeg
    python scripts/build_demo_video.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "demo_video"
FRAMES = OUT / "_frames"
AUDIO = FRAMES / "_audio"
VIDEO = OUT / "bytesize_track4_demo.mp4"
SRT = OUT / "captions.en.srt"
W, H = 1920, 1080
TOTAL = 180.0

VOICE = "en-US-AriaNeural"
VOICE_RATE = "+6%"

BG = (11, 11, 12)
INK = (244, 241, 234)
MUTED = (163, 158, 148)
ACCENT = (254, 44, 85)
CARD = (22, 22, 23)
PANEL = (16, 16, 18)
GREEN = (140, 210, 160)
YELLOW = (232, 196, 110)
BLUE = (120, 190, 235)


# --------------------------------------------------------------------------- #
# Drawing helpers
# --------------------------------------------------------------------------- #


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ("C:/Windows/Fonts/calibrib.ttf", "C:/Windows/Fonts/segoeuib.ttf")
        if bold
        else ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/segoeui.ttf")
    )
    for path in names + ("C:/Windows/Fonts/arial.ttf",):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
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


def canvas(chapter: str, progress: float) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Every frame carries the same chapter label and elapsed-time bar."""

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 14, H), fill=ACCENT)

    draw.text((56, 44), chapter.upper(), font=font(24, True), fill=ACCENT)
    draw.text(
        (W - 56, 44),
        "ByteSize  ·  Track 4  ·  TikTok TechJam 2026",
        font=font(24),
        fill=MUTED,
        anchor="ra",
    )
    draw.line((56, 88, W - 56, 88), fill=(38, 38, 40), width=2)

    bar_y = H - 34
    draw.line((56, bar_y, W - 56, bar_y), fill=(38, 38, 40), width=4)
    filled = 56 + (W - 112) * max(0.0, min(1.0, progress))
    draw.line((56, bar_y, filled, bar_y), fill=ACCENT, width=4)
    return img, draw


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        for word in para.split(" "):
            trial = word if not cur else f"{cur} {word}"
            if draw.textlength(trial, font=fnt) <= width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


def block(
    draw: ImageDraw.ImageDraw,
    text: str,
    fnt,
    fill: tuple[int, int, int],
    x: int,
    y: int,
    width: int,
    leading: int,
) -> int:
    for line in wrap(draw, text, fnt, width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += leading
    return y


def save(img: Image.Image, name: str) -> Path:
    FRAMES.mkdir(parents=True, exist_ok=True)
    path = FRAMES / name
    img.save(path, "PNG")
    return path


def arrow(draw: ImageDraw.ImageDraw, x: int, y0: int, y1: int) -> None:
    draw.line((x, y0, x, y1 - 12), fill=(70, 70, 74), width=3)
    draw.polygon(
        [(x - 9, y1 - 14), (x + 9, y1 - 14), (x, y1)], fill=(110, 110, 116)
    )


# --------------------------------------------------------------------------- #
# Cards
# --------------------------------------------------------------------------- #


def card_problem(progress: float) -> Path:
    img, draw = canvas("01  Problem", progress)
    draw.text((56, 170), "Shopping search asks the wrong thing", font=font(56, True), fill=INK)

    panels = [
        (56, "FILTER WALLS", "You translate what you want\ninto someone else's taxonomy.", MUTED),
        (700, "CHATTY AI", "Ten turns of interrogation\nbefore anything is shown.", MUTED),
        (1344, "THE COST", "Patience. The one thing a\nshopper will not give twice.", ACCENT),
    ]
    for x, head, body, colour in panels:
        draw.rounded_rectangle((x, 300, x + 520, 640), radius=14, fill=CARD)
        draw.text((x + 36, 344), head, font=font(24, True), fill=colour)
        yy = 410
        for line in body.split("\n"):
            draw.text((x + 36, yy), line, font=font(30), fill=INK)
            yy += 46

    # The turn tax is the whole reason stopping early is worth modelling, so
    # show the rule that charges for it rather than only asserting it.
    draw.rounded_rectangle((56, 710, 1864, 900), radius=14, fill=PANEL)
    draw.text(
        (88, 748),
        "THE SCORING RULE AGREES \u2014 EVERY EXTRA TURN IS TAXED",
        font=font(24, True),
        fill=MUTED,
    )
    draw.text(
        (88, 800),
        "TechnicalScore = 0.50 \u00d7 Hit@10  +  0.30 \u00d7 MRR  +  0.20 \u00d7 Efficiency",
        font=mono(30),
        fill=INK,
    )
    draw.text(
        (88, 848),
        "Efficiency = clip((11 \u2212 MTTC) / 10, 0, 1)",
        font=mono(28),
        fill=ACCENT,
    )
    return save(img, "01_problem.png")


def card_solution(progress: float) -> Path:
    img, draw = canvas("02  Our Solution", progress)
    y = block(
        draw,
        "Stop optimizing how the agent ranks.\nStart optimizing when it knows enough to rank.",
        font(52, True),
        INK,
        56,
        170,
        1780,
        74,
    )
    draw.line((56, y + 20, 900, y + 20), fill=ACCENT, width=4)

    y = block(
        draw,
        "Every turn resolves one decision: is another question worth more than another guess? "
        "We model that explicitly as value of information.",
        font(32),
        MUTED,
        56,
        y + 60,
        1780,
        46,
    )

    # The decision rule itself, rather than a dead band between claim and stats.
    draw.rounded_rectangle((56, y + 44, 1864, y + 226), radius=14, fill=PANEL)
    draw.text(
        (96, y + 84),
        "while another answer would still change the ranking",
        font=mono(30),
        fill=INK,
    )
    draw.text((1180, y + 84), "\u2192   ask", font=mono(30), fill=YELLOW)
    draw.text(
        (96, y + 148),
        "the moment it would not",
        font=mono(30),
        fill=INK,
    )
    draw.text((1180, y + 148), "\u2192   recommend", font=mono(30), fill=GREEN)

    stats = [
        (56, "2.75", "turns to converge", "budget is 10"),
        (656, "0", "LLM tokens", "$0 per session"),
        (1256, "100%", "public Hit@10", "200 sessions"),
    ]
    for x, big, label, sub in stats:
        draw.rounded_rectangle((x, 760, x + 560, 960), radius=14, fill=CARD)
        cx = x + 280
        draw.text((cx, 826), big, font=font(68, True), fill=INK, anchor="mm")
        draw.text((cx, 892), label, font=font(28), fill=INK, anchor="mm")
        draw.text((cx, 930), sub, font=font(22), fill=MUTED, anchor="mm")
    return save(img, "02_solution.png")


def card_architecture(progress: float) -> Path:
    img, draw = canvas("03  Architecture", progress)
    draw.text((56, 130), "Five deterministic stages", font=font(46, True), fill=INK)

    stages = [
        ("1  Dialogue state", "slots  ·  scoped intent override  ·  scenario", BLUE),
        ("2  Exact-evidence AND", "category lock  ·  verbatim conjunction  ·  hard pool", BLUE),
        ("3  Value-of-Information controller", "evidence insufficient → ask  ·  sufficient → recommend", ACCENT),
        ("4  Popularity-first late fusion", "popularity 1.0 + field 0.35 + phrase 0.15 + MiniLM 0.1", GREEN),
        ("5  Optional listwise LLM", "shortlist ≤ 10  ·  shipped disabled", MUTED),
    ]
    y = 230
    for head, body, colour in stages:
        draw.rounded_rectangle((56, y, 1400, y + 118), radius=12, fill=CARD)
        draw.rectangle((56, y, 62, y + 118), fill=colour)
        draw.text((96, y + 24), head, font=font(30, True), fill=INK)
        draw.text((96, y + 68), body, font=font(24), fill=MUTED)
        if y < 700:
            arrow(draw, 728, y + 118, y + 148)
        y += 148

    draw.rounded_rectangle((1450, 230, 1864, 810), radius=12, fill=PANEL)
    draw.text((1482, 266), "INVARIANTS", font=font(24, True), fill=ACCENT)
    notes = [
        "Standard library only\non the scored path.",
        "MiniLM is late fusion —\nnever recall, never a\npopularity override.",
        "The controller never reads\nthe remaining turn budget.",
        "rank() is frozen.",
    ]
    yy = 320
    for note in notes:
        for line in note.split("\n"):
            draw.text((1482, yy), line, font=font(24), fill=INK)
            yy += 34
        yy += 22
    return save(img, "03_architecture.png")


def card_results(progress: float) -> Path:
    img, draw = canvas("05  Results", progress)
    draw.text((56, 130), "The number we actually trust", font=font(46, True), fill=INK)

    draw.text((56, 210), "Hit@10  ·  public 200", font=font(24, True), fill=MUTED)
    bars = [("Weak BM25 starter", 0.125, MUTED), ("ByteSize ContestAgent", 1.000, ACCENT)]
    y = 254
    for label, value, colour in bars:
        draw.text((56, y), label, font=font(26), fill=INK)
        draw.rounded_rectangle((620, y - 4, 620 + int(1000 * value), y + 34), radius=6, fill=colour)
        draw.text((1640, y), f"{value:.3f}", font=font(28, True), fill=INK)
        y += 62

    boxes = [
        (56, "+60", "Rank-1 gained", "800 unseen sessions"),
        (656, "8 / 8", "shards improved", "ID-disjoint"),
        (1256, "0", "Hit-rate lost", "strict improvement"),
    ]
    for x, big, label, sub in boxes:
        draw.rounded_rectangle((x, 420, x + 560, 630), radius=14, fill=CARD)
        cx = x + 280
        draw.text((cx, 490), big, font=font(68, True), fill=INK, anchor="mm")
        draw.text((cx, 560), label, font=font(28), fill=INK, anchor="mm")
        draw.text((cx, 598), sub, font=font(22), fill=MUTED, anchor="mm")

    rows = [
        ("Split", "n", "Hit@10", "MRR", "MTTC", "Score", "Rank-1"),
        ("Public", "200", "1.000", "0.954167", "2.75", "0.95125", "184"),
        ("Our holdout", "200", "0.980", "0.864845", "2.885", "0.911753", "162"),
        ("Random 800", "800", "0.97375", "0.888018", "2.8975", "0.91533", "672"),
    ]
    cols = [80, 340, 470, 700, 990, 1220, 1560]
    draw.rounded_rectangle((56, 670, 1864, 940), radius=12, fill=CARD)
    for r, row in enumerate(rows):
        yy = 700 + r * 58
        colour = MUTED if r == 0 else INK
        fnt = font(26, True) if r <= 1 else font(26)
        for c, cell in enumerate(row):
            draw.text((cols[c], yy), cell, font=fnt, fill=colour)
    return save(img, "05_results.png")


def card_impact(progress: float) -> Path:
    img, draw = canvas("06  Impact", progress)
    draw.text((56, 150), "Why this scales past the hackathon", font=font(48, True), fill=INK)

    panels = [
        (56, "COST STRUCTURE", "Zero marginal inference cost.\nAn LLM every turn cannot be\ndeployed to millions of\nsessions a day. This can.", ACCENT),
        (700, "PRIVACY & REACH", "Offline on commodity CPU.\nNo shopping intent leaves\nthe process. No vendor, no\nrate limit, no dead region.", BLUE),
        (1344, "PORTABILITY", "The controller reasons about\nevidence, not about clothing.\nSwap the catalog, keep\nthe policy.", GREEN),
    ]
    for x, head, body, colour in panels:
        draw.rounded_rectangle((x, 250, x + 520, 690), radius=14, fill=CARD)
        draw.text((x + 36, 292), head, font=font(24, True), fill=colour)
        yy = 356
        for line in body.split("\n"):
            draw.text((x + 36, yy), line, font=font(27), fill=INK)
            yy += 44

    draw.text(
        (56, 760),
        "Knowing when to stop asking is a modelable decision — and modelling it beats tuning a ranker.",
        font=font(34),
        fill=INK,
    )
    draw.rounded_rectangle((56, 840, 1180, 926), radius=8, fill=PANEL)
    draw.text((84, 864), "python -m evaluator.local_evaluator", font=mono(30), fill=INK)
    draw.text(
        (1220, 866),
        "ByteSize  ·  contest/public  ·  reproducible locally",
        font=font(26),
        fill=MUTED,
    )
    return save(img, "06_impact.png")


REVEAL = 0.5  # seconds a freshly typed line holds before the next one lands


def term_still(
    name: str,
    heading: str,
    body: list[str],
    footer: str,
    progress: float,
    shown: int,
    partial: str | None = None,
    caret: bool = False,
) -> Path:
    """One frame of the terminal, holding the first `shown` lines of body.

    `partial` truncates the last visible line mid-sentence so the customer's
    message can be seen arriving; `caret` parks a block cursor after it.
    """

    img, draw = canvas("04  Live Demo", progress)
    draw.text((56, 130), heading, font=font(38, True), fill=INK)
    draw.text(
        (W - 56, 140),
        "official simulator  \u00b7  public_0002  \u00b7  intent override",
        font=font(24),
        fill=ACCENT,
        anchor="ra",
    )
    draw.rounded_rectangle((56, 200, 1864, 880), radius=12, fill=PANEL)
    y = 232
    fnt = mono(26)
    visible = body[:shown]
    for index, line in enumerate(visible):
        if partial is not None and index == len(visible) - 1:
            line = partial
        colour = INK
        if line.startswith("customer:"):
            colour = YELLOW
        elif line.startswith("agent:"):
            colour = GREEN
        elif "<= TARGET" in line or line.startswith("HIT"):
            colour = ACCENT
        elif line.startswith(("ask=", "usage", "[", "scope=", "scenario=", "target=", "---")):
            colour = MUTED
        text = line[:112]
        draw.text((88, y), text, font=fnt, fill=colour)
        if caret and index == len(visible) - 1:
            x = 88 + draw.textlength(text, font=fnt)
            draw.rectangle((x + 5, y + 4, x + 17, y + 30), fill=MUTED)
        y += 38
        if y > 850:
            break
    draw.text((56, 910), footer, font=font(26), fill=MUTED)
    return save(img, name)


def term_frames(
    stem: str,
    heading: str,
    body: list[str],
    footer: str,
    progress: float,
) -> list[tuple[Path, float | None]]:
    """Type the turn out line by line instead of cutting to a finished card.

    A still card only claims a demo. Watching the customer's message arrive,
    the pool collapse, and the ranked rows land one at a time is the demo.
    Reveal frames are short and fixed; the completed card takes whatever is
    left of the segment, so the narration still plays over the full state.
    """

    steps: list[tuple[int, str | None]] = []
    for index, line in enumerate(body):
        if not line.strip():
            continue
        # The customer's own words type in. Machine output lands whole.
        if line.startswith("customer:") and len(line) > 34:
            steps.append((index + 1, line[: len(line) * 2 // 3]))
        steps.append((index + 1, None))

    frames: list[tuple[Path, float | None]] = []
    for n, (shown, partial) in enumerate(steps):
        last = n == len(steps) - 1
        frames.append(
            (
                term_still(
                    f"{stem}_{n:02d}.png",
                    heading,
                    body,
                    # The verdict line is the punchline; it waits for the
                    # rows that earn it rather than spoiling them.
                    footer if last else "",
                    progress,
                    shown,
                    partial,
                    caret=not last,
                ),
                None if last else REVEAL,
            )
        )
    return frames


# --------------------------------------------------------------------------- #
# Storyboard
# --------------------------------------------------------------------------- #


@dataclass
class Segment:
    key: str
    chapter: str
    target: float
    narration: str
    render: object
    duration: float = 0.0
    start: float = 0.0
    audio: Path | None = field(default=None)


def storyboard() -> list[Segment]:
    demo = [
        (
            "d0",
            9.0,
            "This is the organizers' own simulator — no mock-up, no website. Session public zero zero "
            "two, the Intent Override scenario.",
            "Setup  ·  0 tokens",
            [
                "scenario=intent_override   sample=public_0002",
                "target=B071X54486  Hide & Drink full grain leather belt",
                "",
                "ask_attribute is always other. Ranking waits for evidence.",
            ],
            "The same evaluator the organizers ship. Nothing simulated by us.",
        ),
        (
            "d1",
            13.0,
            "Turn one. The customer wants a belt with a buckle closure. That matches two hundred fifty-eight "
            "products, so the agent withholds the list entirely and asks about material.",
            "Turn 1  ·  withhold",
            [
                "customer: I'm looking for Accessories Belts. Buckle closure",
                "agent:    Matching Accessories Belts — buckle closure.",
                "          What material or fabric should I match?",
                "",
                "ask=other  pool=258  hard=111  withhold=True  usage=0",
            ],
            "Pool is still large. Do not dump a ranked list yet.",
        ),
        (
            "d2",
            14.0,
            "Turn two. Leather is disclosed and the hard pool collapses from two hundred fifty-eight to "
            "twenty-two. A weaker agent would answer here. Ours calculates that one more question still wins.",
            "Turn 2  ·  still gathering",
            [
                "customer: For that, what matters is: leather; 100% Leather.",
                "agent:    Matching Accessories Belts — leather; 100% leather.",
                "          Any colour or print I should lock in?",
                "",
                "ask=other  pool=258  hard=22  withhold=True  usage=0",
            ],
            "Hard pool 258 → 22. Twenty-two near-identical belts is still a coin flip.",
        ),
        (
            "d3",
            13.0,
            "Turn three: the customer changes their mind. The state replaces the old preference instead "
            "of appending a contradiction, and any hit scored before it is discarded.",
            "Turn 3  ·  override replaces state",
            [
                "[simulator] intent override",
                "customer: Actually, ignore my earlier preference.",
                "          What I need is: leather.",
                "agent:    I'll follow the updated requirement.",
                "",
                "scope=referenced_preference_replace  withhold=True  usage=0",
            ],
            "Slots are replaced, not appended. Hits before an override cannot score.",
        ),
        (
            "d4",
            16.0,
            "Turn four. Two more attributes arrive, the hard pool drops to seven, and the controller decides "
            "the evidence is sufficient. It recommends — and the target belt comes back at rank one.",
            "Turn 4  ·  evidence is enough",
            [
                "customer: For that, what matters is: Imported; Buckle closure.",
                "agent:    Here are the closest matches so far.",
                "",
                "ask=other  hard=7  withhold=False  usage=0",
                "  1. B071X54486  Hide & Drink Full Grain Leather Belt   <= TARGET",
                "  2. B072M9PJ3H  find. Men's Leather Formal Belt",
                "  3. B016B07WZI  Dona Michi MEN'S WORK BELT",
            ],
            "Recommend now. Target is rank 1.",
        ),
        (
            "d5",
            8.0,
            "That is the whole idea: ask while the answer would change the ranking, and stop the moment "
            "it would not.",
            "HIT  ·  turn 4  ·  rank 1",
            [
                "--- outcome ---",
                "HIT   turn=4   rank=1",
                "usage prompt_tokens=0  completion_tokens=0",
            ],
            "Value-of-information stop, on the organizers' own harness.",
        ),
    ]

    segments: list[Segment] = [
        Segment(
            "problem",
            "01  Problem",
            17.0,
            "Online shopping has a conversation problem. Filter walls make you translate what you want into "
            "someone else's categories. AI assistants do the opposite, interrogating you for ten turns "
            "before showing anything. Both burn the one thing shoppers will not give twice: patience.",
            card_problem,
        ),
        Segment(
            "solution",
            "02  Our Solution",
            22.0,
            "So we stopped optimizing how our agent ranks products, and started optimizing when it knows "
            "enough to rank at all. Every turn resolves one question: is another question worth more than "
            "another guess? Modelling that value-of-information decision explicitly is our core "
            "contribution. It converges in under three turns, at zero tokens.",
            card_solution,
        ),
        Segment(
            "architecture",
            "03  Architecture",
            25.0,
            "Five deterministic stages. Dialogue state tracks slots and intent overrides. An exact-evidence "
            "conjunction builds the hard pool. The value-of-information controller then decides: ask, or "
            "recommend. Ranking is popularity-first late fusion, with a local MiniLM encoder adding a small "
            "cosine adjustment. The optional language model rerank ships disabled.",
            card_architecture,
        ),
    ]

    for key, target, narration, heading, body, footer in demo:
        segments.append(
            Segment(
                key,
                "04  Live Demo",
                target,
                narration,
                lambda progress, k=key, h=heading, b=body, f=footer: term_frames(
                    f"04_{k}", h, b, f, progress
                ),
            )
        )

    segments.append(
        Segment(
            "results",
            "05  Results",
            25.0,
            "The weak baseline finds the target twelve percent of the time. We find it every time on the "
            "public set, at a technical score of zero point nine five. But the number we actually trust is "
            "this one: across eight hundred unseen, identifier-disjoint sessions, our stopping controller "
            "delivered sixty additional rank-one recommendations with zero Hit-rate loss, improving on all "
            "eight of eight shards.",
            card_results,
        )
    )
    segments.append(
        Segment(
            "impact",
            "06  Impact",
            18.0,
            "Zero marginal inference cost means this deploys at marketplace scale, not demo scale. It runs "
            "offline on commodity CPU, so no shopping intent leaves the process. And the controller is "
            "catalog agnostic.",
            card_impact,
        )
    )
    return segments


# --------------------------------------------------------------------------- #
# Voice-over
# --------------------------------------------------------------------------- #


def _clean(text: str) -> str:
    return text.replace("—", ",").replace("·", " ")


def tts_edge(text: str, dest: Path) -> bool:
    try:
        import asyncio

        import edge_tts
    except Exception:
        return False
    try:

        async def run() -> None:
            speech = edge_tts.Communicate(_clean(text), VOICE, rate=VOICE_RATE)
            await speech.save(str(dest))

        asyncio.run(run())
        return dest.is_file() and dest.stat().st_size > 2048
    except Exception as exc:  # network, voice name, or API drift
        print(f"  edge-tts failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def tts_sapi(text: str, dest: Path) -> bool:
    """Offline Windows fallback. Robotic, but never needs the network."""

    if sys.platform != "win32":
        return False
    wav = dest.with_suffix(".wav")
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.Rate = 1;"
        f"$s.SetOutputToWaveFile('{wav.as_posix()}');"
        f"$s.Speak([Console]::In.ReadToEnd());"
        "$s.Dispose()"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            input=_clean(text),
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            capture_output=True,
            timeout=180,
        )
    except Exception as exc:
        print(f"  SAPI failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False
    if not wav.is_file() or wav.stat().st_size < 2048:
        return False
    shutil.move(str(wav), str(dest))
    return True


def synthesise(segments: list[Segment]) -> str:
    AUDIO.mkdir(parents=True, exist_ok=True)
    engine = "edge-tts"
    for seg in segments:
        dest = AUDIO / f"{seg.key}.mp3"
        if tts_edge(seg.narration, dest):
            seg.audio = dest
            continue
        if tts_sapi(seg.narration, dest):
            seg.audio = dest
            engine = "windows-sapi"
            continue
        seg.audio = None
        engine = "none"
    if engine == "none":
        print("no TTS backend available; rendering a silent video", file=sys.stderr)
        print("  python -m pip install edge-tts", file=sys.stderr)
    else:
        print(f"voice-over engine: {engine}")
    return engine


# --------------------------------------------------------------------------- #
# ffmpeg
# --------------------------------------------------------------------------- #


def find_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise SystemExit("ffmpeg not found. python -m pip install imageio-ffmpeg")


def run(
    cmd: list[str], check: bool = True, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    # Pin the pipe encoding. ffmpeg's banner carries a non-ASCII (R), and on a
    # non-UTF-8 Windows codepage Python decodes the pipe with the ANSI codepage,
    # kills the reader thread mid-stream, and hands back proc.stderr = None.
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd) if cwd else None,
    )
    if check and proc.returncode != 0:
        print(f"ffmpeg failed: {' '.join(cmd[1:])}", file=sys.stderr)
        print(proc.stderr[-1200:], file=sys.stderr)
        raise SystemExit(proc.returncode)
    return proc


def media_duration(ffmpeg: str, path: Path) -> float:
    """Parse the last reported timestamp; works on any ffmpeg build."""

    proc = run([ffmpeg, "-i", str(path), "-f", "null", "-"], check=False)
    stamps = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", proc.stderr)
    if not stamps:
        return 0.0
    hours, minutes, seconds = stamps[-1]
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def plan(ffmpeg: str, segments: list[Segment]) -> None:
    """Slide length follows the narration, so audio and visuals cannot drift.

    The storyboard targets sum to exactly 180s, so any segment whose narration
    runs long would push the tail past the hard trim and cut the closing line.
    Reclaim the overrun from padding rather than from speech: every segment can
    shrink toward its own floor of narration + 0.35s, never below it.
    """

    spoken = {
        seg.key: (media_duration(ffmpeg, seg.audio) if seg.audio else 0.0)
        for seg in segments
    }
    for seg in segments:
        seg.duration = max(seg.target, spoken[seg.key] + 0.7)

    total = sum(seg.duration for seg in segments)
    if total > TOTAL:
        floors = {key: value + 0.35 for key, value in spoken.items()}
        slack = sum(seg.duration - floors[seg.key] for seg in segments)
        excess = total - TOTAL
        if slack >= excess:
            for seg in segments:
                seg.duration -= (seg.duration - floors[seg.key]) * excess / slack
            print(f"reclaimed {excess:.1f}s of padding to hold {TOTAL:.0f}s")
        else:
            print(
                f"narration alone runs {total - slack + excess:.1f}s; "
                f"shorten it or the tail is trimmed at {TOTAL:.0f}s",
                file=sys.stderr,
            )

    clock = 0.0
    for seg in segments:
        seg.duration = round(seg.duration, 3)
        seg.start = round(clock, 3)
        clock += seg.duration
        over = "" if spoken[seg.key] <= seg.target else f"  (voice {spoken[seg.key]:.1f}s > target {seg.target:.0f}s)"
        print(f"  {seg.key:<12} {seg.duration:6.2f}s{over}")
    print(f"  {'TOTAL':<12} {clock:6.2f}s")


def build_audio(ffmpeg: str, segments: list[Segment]) -> Path | None:
    """Pad every narration clip out to its slide length, then concatenate."""

    if not any(seg.audio for seg in segments):
        return None
    parts: list[Path] = []
    for seg in segments:
        part = AUDIO / f"{seg.key}_padded.wav"
        if seg.audio:
            run(
                [ffmpeg, "-y", "-i", str(seg.audio), "-af", "apad",
                 "-t", f"{seg.duration:.3f}", "-ar", "48000", "-ac", "2", str(part)]
            )
        else:
            run(
                [ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                 "-t", f"{seg.duration:.3f}", str(part)]
            )
        parts.append(part)

    listing = AUDIO / "concat.txt"
    listing.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in parts) + "\n", encoding="utf-8"
    )
    track = AUDIO / "voiceover.wav"
    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(track)])
    return track


CAPTION_STYLE = (
    "FontName=Calibri,FontSize=17,PrimaryColour=&H00EAF1F4,"
    "OutlineColour=&H00160B0B,BorderStyle=1,Outline=2,Shadow=0,MarginV=58"
)


def build_video(
    ffmpeg: str,
    segments: list[Segment],
    frames: list[list[tuple[Path, float | None]]],
) -> Path:
    """Concatenate the stills and burn captions in a single 1080p encode.

    The subtitles filter is run from inside _frames against a bare ASCII
    filename. A filtergraph path cannot safely carry the drive colon, spaces,
    or the CJK characters in this repository's own path, and a failure there is
    silent apart from a warning, so the captions would quietly disappear.
    """

    listing = FRAMES / "concat.txt"
    lines: list[str] = []
    for shots, seg in zip(frames, segments):
        # Reveal frames are fixed-length, but never at the cost of the state
        # the narration describes: the finished card keeps half the segment.
        fixed = sum(hold for _, hold in shots if hold is not None)
        budget = seg.duration * 0.5
        scale = 1.0 if fixed <= budget else budget / fixed
        rest = seg.duration - fixed * scale
        for path, hold in shots:
            span = rest if hold is None else hold * scale
            lines.append(f"file '{path.as_posix()}'")
            lines.append(f"duration {span:.3f}")
    lines.append(f"file '{frames[-1][-1][0].as_posix()}'")
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")

    subs = FRAMES / "subs.srt"
    shutil.copyfile(SRT, subs)

    dest = FRAMES / "raw.mp4"
    source = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing)]
    encode = [
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", dest.name,
    ]
    captioned = f"fps=30,subtitles={subs.name}:force_style='{CAPTION_STYLE}',format=yuv420p"

    proc = run(source + ["-vf", captioned] + encode, check=False, cwd=FRAMES)
    if proc.returncode == 0:
        return dest

    print("captions not burned; upload captions.en.srt on YouTube instead", file=sys.stderr)
    print(proc.stderr[-600:], file=sys.stderr)
    run(source + ["-vf", "fps=30,format=yuv420p"] + encode, cwd=FRAMES)
    return dest


def finish(ffmpeg: str, video: Path, track: Path | None, dest: Path) -> None:
    final = FRAMES / "final.mp4"
    cmd = [ffmpeg, "-y", "-i", str(video)]
    if track:
        cmd += ["-i", str(track), "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-t", f"{TOTAL:.0f}", "-c:v", "copy", "-movflags", "+faststart", str(final)]
    proc = run(cmd, check=False)
    if proc.returncode != 0:
        cmd[cmd.index("copy")] = "libx264"
        run(cmd)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(final, dest)


# --------------------------------------------------------------------------- #
# Captions
# --------------------------------------------------------------------------- #


CAPTION_LIMIT = 84      # characters per cue, comfortable over two lines
MIN_CUE = 1.2           # seconds; a shorter cue is gone before it can be read

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_CLAUSE = re.compile(r"(?<=[,;:])\s+|\s+\u2014\s+")


def _units(text: str, limit: int) -> list[str]:
    """Split narration where the voice actually pauses.

    Sentences first, then clause punctuation, and only as a last resort mid
    phrase. No unit exceeds the limit, so packing them can never overflow.
    """

    units: list[str] = []
    for sentence in _SENTENCE.split(text.strip()):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= limit:
            units.append(sentence)
            continue
        for clause in _CLAUSE.split(sentence):
            clause = clause.strip()
            if not clause:
                continue
            if len(clause) <= limit:
                units.append(clause)
                continue
            line = ""
            for word in clause.split():
                trial = word if not line else f"{line} {word}"
                if len(trial) <= limit:
                    line = trial
                else:
                    units.append(line)
                    line = word
            if line:
                units.append(line)
    return units


def caption_chunks(text: str, limit: int = CAPTION_LIMIT) -> list[str]:
    """Cue text that starts and ends on a pause.

    Packing purely by width strands the tail of a sentence in a cue of its
    own, the 0.6s "patience." that flashes past unread. Cut on pauses, then
    glue neighbouring units back together while they still fit.
    """

    cues: list[str] = []
    for unit in _units(text, limit):
        if cues and len(cues[-1]) + 1 + len(unit) <= limit:
            cues[-1] = f"{cues[-1]} {unit}"
        else:
            cues.append(unit)
    return cues


def merge_short_cues(
    cues: list[str], duration: float, minimum: float = MIN_CUE
) -> list[str]:
    """Fold away any cue too brief to read.

    A cue's span is proportional to its length, so the shortest cue is also
    the shortest-lived. Merge it into the cue before it, or into the one after
    when it is first, until every cue survives long enough to be read.
    """

    cues = list(cues)
    while len(cues) > 1:
        total = sum(len(c) for c in cues) or 1
        spans = [duration * len(c) / total for c in cues]
        i = min(range(len(cues)), key=spans.__getitem__)
        if spans[i] >= minimum:
            break
        if i == 0:
            cues[1] = f"{cues[0]} {cues[1]}"
            del cues[0]
        else:
            cues[i - 1] = f"{cues[i - 1]} {cues[i]}"
            del cues[i]
    return cues


def caption_lines(text: str, per_line: int = 46) -> str:
    """Balance a cue across as few lines as it needs, breaking on words."""

    rows = max(1, -(-len(text) // per_line))
    target = -(-len(text) // rows)
    out: list[str] = []
    cur = ""
    for word in text.split():
        trial = word if not cur else f"{cur} {word}"
        if cur and len(trial) > target and len(out) < rows - 1:
            out.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        out.append(cur)
    return "\n".join(out)


def stamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments: list[Segment]) -> None:
    """Captions are cut from the narration, so they always match the voice."""

    blocks: list[str] = []
    index = 1
    for seg in segments:
        chunks = merge_short_cues(caption_chunks(seg.narration), seg.duration)
        weights = [len(c) for c in chunks]
        total = sum(weights) or 1
        cursor = seg.start
        for chunk, weight in zip(chunks, weights):
            span = seg.duration * weight / total
            blocks.append(
                f"{index}\n{stamp(cursor)} --> {stamp(cursor + span)}\n"
                f"{caption_lines(chunk)}\n"
            )
            index += 1
            cursor += span
    SRT.write_text("\n".join(blocks), encoding="utf-8")
    print(f"wrote {SRT.name}  ({index - 1} cues)")


# --------------------------------------------------------------------------- #


def main() -> int:
    FRAMES.mkdir(parents=True, exist_ok=True)
    segments = storyboard()

    print("synthesising narration...")
    synthesise(segments)

    ffmpeg = find_ffmpeg()
    print("timeline:")
    plan(ffmpeg, segments)

    total = sum(seg.duration for seg in segments)
    frames: list[list[tuple[Path, float | None]]] = []
    for seg in segments:
        shot = seg.render(seg.start / total)
        frames.append([(shot, None)] if isinstance(shot, Path) else list(shot))
    count = sum(len(shots) for shots in frames)
    print(f"rendered {count} frames over {len(segments)} slides  \u00b7  {total:.1f}s")

    write_srt(segments)
    track = build_audio(ffmpeg, segments)
    video = build_video(ffmpeg, segments, frames)
    finish(ffmpeg, video, track, VIDEO)

    size = VIDEO.stat().st_size / 1_048_576
    streams = run([ffmpeg, "-i", str(VIDEO), "-f", "null", "-"], check=False).stderr
    has_audio = "Audio:" in streams
    print(f"wrote {VIDEO}  ({size:.1f} MB)")
    print(f"  duration  {media_duration(ffmpeg, VIDEO):.1f}s")
    print(f"  voice-over {'PRESENT' if has_audio else 'MISSING — video is silent'}")
    print("ByteSize · contest/public · reproducible locally")
    return 0 if has_audio else 1


if __name__ == "__main__":
    raise SystemExit(main())
