# 3-minute demo — screen + English captions

**已经合成好的成片：** `report/demo_video/bytesize_track4_demo.mp4`  
（真实 public_0002 回放 + 结果页，不是桌面 Game Bar 录像。Track 4 允许终端 walkthrough。）

上传步骤见 `YOUTUBE.md`。下面是如果你想自己再录一版桌面的备用说明。

不出镜、不配音。YouTube 上传时带上 `captions.en.srt`（设为 English，默认显示）。

目标时长 **2:50–3:00**。官方要求公开 YouTube + Devpost 链接。

## 你要录的四段

| 段 | 时长 | 画面 | 讲什么（字幕已写好） |
|---|---|---|---|
| A | 0:00–0:18 | 幻灯片 1 全屏 | 赛道 + VoI 标题 |
| B | 0:18–0:38 | 幻灯片 2 全屏 | We stopped optimizing how the agent ranks… |
| C | 0:38–2:10 | 终端 `public_0002` | Intent Override，问 other，第 4 轮 Rank-1 |
| D | 2:10–3:00 | 幻灯片 3 然后 4 | +60 Rank-1 / 8/8 shards / 0 token |

幻灯片：`report/demo_video/demo_cards.pptx`  
字幕：`report/demo_video/captions.en.srt`

## 录之前（只做一次，不要出现在成片里）

终端字体调到 **18+**，全屏，深色背景。先预热 MiniLM，避免正片卡 2 分钟：

```powershell
cd "C:\Users\LW\Desktop\课程\nus 黑客松\techjam-conversational-search"
$env:PYTHONPATH = "."
python scripts/record_demo.py --warmup-only
```

应打印 `minilm_available=True`。若 False，先 `python scripts/vendor_minilm.py`。

PowerPoint 打开 `demo_cards.pptx`，幻灯片放映（F5）。

## 怎么录（Windows）

1. `Win + G` 打开 Xbox Game Bar → 开始录制（`Win + Alt + R`）。
2. **段 A/B**：幻灯片 1 停约 18 秒，空格到第 2 页再停约 20 秒。
3. `Alt + Tab` 到终端，运行：

```powershell
python scripts/record_demo.py --pause 2.5 --session public_0002
```

等它打出 `HIT turn=4 rank=1`。
4. 回到 PPT：第 3 页约 25 秒，第 4 页约 15 秒。
5. 再按 `Win + Alt + R` 停止。录像一般在 `Videos\Captures`。

若要剪成准确 3 分钟：用系统自带 **Clipchamp** 按上表裁切。不配乐、不加 TikTok 商标。

## 上传 YouTube

- 可见性：**公开**（或「不列出」仅当 Devpost 明确允许；题面写 public，用公开更稳）
- 标题：`ByteSize — Evidence-Aware Conversational Search (TikTok TechJam 2026 Track 4)`
- 描述第一行：Value-of-Information stopping; +60 Rank-1 / 800; zero Hit-rate loss
- 字幕：上传 `captions.en.srt`，语言 English，设为默认显示
- 把链接贴进 Devpost

不要在画面里露出 API key、私有 holdout、个人路径里的无关窗口。
