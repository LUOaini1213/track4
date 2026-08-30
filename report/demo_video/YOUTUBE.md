# YouTube upload

Video (already built, 3:00, 1920×1080):

`report/demo_video/bytesize_track4_demo.mp4`

Captions: `report/demo_video/captions.en.srt`

## Title
ByteSize — Evidence-Aware Conversational Search (TikTok TechJam 2026 Track 4)

## Description
We stopped optimizing how the agent ranks, and started optimizing when it knows enough to rank.

+60 Rank-1 recommendations across 800 unseen ID-disjoint sessions, with zero Hit-rate loss. Improvement on all 8/8 shards.

Public 200: Hit@10 1.000 · TechnicalScore 0.95125
Holdout 200: Hit@10 0.980 · Score 0.911753 · Rank-1 162

Scored path: starter.agent.Agent → ContestAgent PUBLIC, progress_defer=e123, local MiniLM, 0 LLM tokens.

python -m evaluator.local_evaluator

SHA 11069c6 (algorithm freeze 3a31ace)

## Settings
- Visibility: Public
- Language: English
- Upload captions.en.srt, set as default
- No music, no third-party logos
