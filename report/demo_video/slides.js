const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "ByteSize Track 4 Demo Cards";
pres.author = "ByteSize";

const BG = "0B0B0C";
const INK = "F4F1EA";
const MUTED = "A39E94";
const ACCENT = "FE2C55";
const CARD = "161617";

function addFooter(slide, page) {
  slide.addText("ByteSize  ·  Track 4  ·  TikTok TechJam 2026", {
    x: 0.5, y: 5.22, w: 7.2, h: 0.24,
    fontFace: "Calibri", fontSize: 11, color: MUTED, margin: 0,
  });
  slide.addText(String(page) + " / 4", {
    x: 8.6, y: 5.22, w: 0.9, h: 0.24,
    fontFace: "Calibri", fontSize: 11, color: MUTED, align: "right", margin: 0,
  });
}

// 1. Title
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625, fill: { color: ACCENT }, line: { color: ACCENT },
  });
  s.addText("TIKTOK TECHJAM 2026  ·  TRACK 4", {
    x: 0.55, y: 1.15, w: 9, h: 0.32,
    fontFace: "Calibri", fontSize: 13, color: ACCENT, bold: true,
    charSpacing: 2, margin: 0,
  });
  s.addText("Evidence-Aware Conversational Search\nwith Value-of-Information Stopping", {
    x: 0.55, y: 1.6, w: 8.9, h: 1.7,
    fontFace: "Calibri", fontSize: 28, color: INK, bold: true, margin: 0,
  });
  s.addText("ByteSize  ·  ContestAgent PUBLIC  ·  0 tokens", {
    x: 0.55, y: 3.5, w: 8.9, h: 0.35,
    fontFace: "Calibri", fontSize: 16, color: MUTED, margin: 0,
  });
  addFooter(s, 1);
}

// 2. Punchline
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625, fill: { color: ACCENT }, line: { color: ACCENT },
  });
  s.addText("THE CLAIM", {
    x: 0.55, y: 0.85, w: 9, h: 0.28,
    fontFace: "Calibri", fontSize: 13, color: ACCENT, bold: true,
    charSpacing: 2, margin: 0,
  });
  s.addText("We stopped optimizing how the agent ranks,\nand started optimizing when it knows enough to rank.", {
    x: 0.55, y: 1.35, w: 8.9, h: 1.5,
    fontFace: "Calibri", fontSize: 24, color: INK, bold: true, margin: 0,
  });
  s.addText("Scoring taxes extra turns. E1/E2/E3 still ask — once — only when the expected value of the next other is higher than the MTTC cost.", {
    x: 0.55, y: 3.05, w: 8.9, h: 0.7,
    fontFace: "Calibri", fontSize: 15, color: MUTED, margin: 0,
  });
  addFooter(s, 2);
}

// 3. Results
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625, fill: { color: ACCENT }, line: { color: ACCENT },
  });
  s.addText("800 UNSEEN SESSIONS  ·  8 ID-DISJOINT SHARDS", {
    x: 0.55, y: 0.4, w: 9, h: 0.28,
    fontFace: "Calibri", fontSize: 13, color: ACCENT, bold: true,
    charSpacing: 1.5, margin: 0,
  });

  const cards = [
    { x: 0.55, n: "+60", l: "Rank-1 / 800" },
    { x: 3.7, n: "8 / 8", l: "shards improved" },
    { x: 6.85, n: "0", l: "Hit-rate loss" },
  ];
  for (const c of cards) {
    s.addShape(pres.shapes.RECTANGLE, {
      x: c.x, y: 0.9, w: 2.95, h: 1.85,
      fill: { color: CARD }, line: { color: CARD },
    });
    s.addText(c.n, {
      x: c.x, y: 1.05, w: 2.95, h: 0.95,
      fontFace: "Calibri", fontSize: 36, color: INK, bold: true, align: "center", margin: 0,
    });
    s.addText(c.l, {
      x: c.x, y: 2.05, w: 2.95, h: 0.4,
      fontFace: "Calibri", fontSize: 14, color: MUTED, align: "center", margin: 0,
    });
  }

  s.addTable(
    [
      [
        { text: "Split", options: { fill: { color: CARD }, color: MUTED, bold: true } },
        { text: "Hit@10", options: { fill: { color: CARD }, color: MUTED, bold: true } },
        { text: "MRR", options: { fill: { color: CARD }, color: MUTED, bold: true } },
        { text: "Score", options: { fill: { color: CARD }, color: MUTED, bold: true } },
        { text: "Rank-1", options: { fill: { color: CARD }, color: MUTED, bold: true } },
      ],
      [
        { text: "Public 200", options: { color: INK } },
        { text: "1.000", options: { color: INK } },
        { text: "0.954167", options: { color: INK } },
        { text: "0.95125", options: { color: INK, bold: true } },
        { text: "184", options: { color: INK } },
      ],
      [
        { text: "Holdout 200", options: { color: INK } },
        { text: "0.980", options: { color: INK } },
        { text: "0.864845", options: { color: INK } },
        { text: "0.911753", options: { color: INK, bold: true } },
        { text: "162", options: { color: INK } },
      ],
    ],
    {
      x: 0.55, y: 3.0, w: 8.9, h: 1.85,
      colW: [2.1, 1.6, 1.8, 1.8, 1.6],
      border: { pt: 0, color: BG },
      fontFace: "Calibri",
      fontSize: 13,
      color: INK,
      align: "left",
      valign: "middle",
    }
  );
  addFooter(s, 3);
}

// 4. Close
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625, fill: { color: ACCENT }, line: { color: ACCENT },
  });
  s.addText("SCORED PATH", {
    x: 0.55, y: 0.85, w: 9, h: 0.28,
    fontFace: "Calibri", fontSize: 13, color: ACCENT, bold: true,
    charSpacing: 2, margin: 0,
  });
  s.addText("starter.agent.Agent  →  ContestAgent PUBLIC\nprogress_defer = e123   ·   MiniLM late fusion   ·   0 LLM tokens", {
    x: 0.55, y: 1.3, w: 8.9, h: 1.0,
    fontFace: "Calibri", fontSize: 18, color: INK, margin: 0,
  });
  s.addText("python -m evaluator.local_evaluator", {
    x: 0.55, y: 2.5, w: 8.9, h: 0.45,
    fontFace: "Consolas", fontSize: 18, color: INK, margin: 0,
  });
  s.addText("ByteSize  ·  contest/public  ·  reproducible locally\nAlways ask other. Verbatim AND. Do not rank until the evidence is enough.", {
    x: 0.55, y: 3.2, w: 8.9, h: 0.85,
    fontFace: "Calibri", fontSize: 15, color: MUTED, margin: 0,
  });
  addFooter(s, 4);
}

pres.writeFile({ fileName: "report/demo_video/demo_cards.pptx" })
  .then(() => console.log("wrote report/demo_video/demo_cards.pptx"))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
