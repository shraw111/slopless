# slopless · Signal Shorts

A mobile swipe feed of the best 60–90 seconds from genuinely high-quality YouTube videos.
Quality over quantity: no trending slop.

**Feed:** https://shraw111.github.io/slopless/

## How it works

- `topics.yaml` holds the topics and the quality thresholds. Only `enabled: true` topics run.
- `pipeline.py` is the one script: find (YouTube Data API + [HackerTube](https://hackertube.org/data)
  for `hn_boost` topics) → cut the noise → label (Haiku sub-agents) → transcripts or chapter fallback →
  score and pick a clip (Sonnet sub-agents) → select → `clips.json` + `topics.json`.
- The pipeline's working data (video cache, transcripts, queries, state) lives in the **private** repo
  `shraw111/slopless-data`, cloned next to this one, because it holds YouTube's own data (metadata,
  captions) that YouTube's terms don't allow republishing. Re-runs skip finished videos, so adding a
  topic only costs that topic. Only `clips.json` and `topics.json` are public.
- `index.html` is the feed. It reads `clips.json` and `topics.json` (no hardcoded topics) and is
  deployed by GitHub Pages from `main`.
- `CLAUDE.md` is the step-by-step runbook Claude Code follows.

Needs `YOUTUBE_API_KEY` as an environment variable. Never commit it.

## How to add a topic

1. Copy a topic block in `topics.yaml` (the disabled `parenting` one is a good template) and edit
   `id`, `name`, `covers`, `exclude` and `good_clip`. Optionally add `queries`, `trusted_channels`,
   `hn_boost: true`, or override any default (e.g. `max_age_months: 60`).
2. Set `enabled: true`.
3. Start a Claude Code session on this repo and say **"Run the pipeline for new topics."**

Claude will show you the search queries it wrote before spending API quota, then stop after the first
10 clips of the new topic so you can check them before it fills the rest.

## Levels, learning paths, debates and Listen

- **Levels:** Haiku tags every clip intro, intermediate or advanced, judged by the background a viewer needs.
  The Level chip in the feed filters on it.
- **Learning paths:** Sonnet writes ordered sequences from the basics to depth (`paths.json`). Browse → Paths.
- **Debates:** Sonnet finds questions where speakers in the clips really disagree (`debates.json`), then a second
  Sonnet pass checks each side against the words actually spoken in its clips and drops anything it can't back.
  Browse → Debates.
- **Listen:** the browser's built-in voice reads each clip's summary aloud. Nothing is sent anywhere.

## Get real transcripts (run on your own computer)

YouTube blocks transcript requests from cloud servers, so the cloud run picks clips from chapters and the
"Most replayed" heatmap, which gives approximate start times. Transcripts give exact cuts and let every
candidate be used. From your laptop (no API key needed for this step):

```bash
git clone https://github.com/shraw111/slopless
git clone https://github.com/shraw111/slopless-data   # private: pipeline data, sits next to it
cd slopless
pip install -r requirements.txt
python pipeline.py transcripts --retry     # fetches captions for every candidate, ~1 s each
cd ../slopless-data && git add data && git commit -m "Add transcripts" && git push
```

Then start a Claude Code session on the repo and say **"Re-score the videos that now have transcripts."**
Videos that got a transcript lose their old score, so the normal scoring step picks them up again.

## Thresholds (defaults in `topics.yaml`)

| filter | value |
|---|---|
| minimum length | 8 min |
| maximum age | 24 months (Parenting: 60) |
| minimum views | 5,000 (1,000 if Hacker News recommended it) |
| minimum like/view ratio | 1.5% (skipped when likes are hidden) |
| candidates scored per topic | top 100 by engagement rank |
| minimum substance | 7 / 10 (+1 for HN-recommended on `hn_boost` topics, or trusted channels) |
| max videos per channel | 5 (a channel's videos, not clips) |
| clips per video | up to 20: one per 10 minutes of video, one per chapter without a transcript, each must clear the substance bar |
| reserve | clips that clear the bar but are held back by the limits (per subject, per channel, per topic) are still published, flagged `more`. They stay out of the main feed and only appear in "More on this subject", "Whole talk in order", search, Browse and channel pages |
| max clips per subject | 2 (Haiku merges near-identical subjects, e.g. every attention explainer) |
| only clips whose words were seen | yes: transcript or chapters, not heatmap alone |
| clips per topic | 50 |

Engagement rank (used to keep the top 100): `log10(views) + 60·likes/views + 200·comments/views (+1 if HN)`.

## Credits

Hacker News recommendations come from the [HackerTube](https://hackertube.org) data export
(ODC-By 1.0), built from the [open-index/hacker-news](https://huggingface.co/datasets/open-index/hacker-news)
dataset. Video data from YouTube.
