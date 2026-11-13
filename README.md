# slopless · Signal Shorts

A mobile swipe feed of the best 60–90 seconds from genuinely high-quality YouTube videos.
Quality over quantity: no trending slop.

**Feed:** https://shraw111.github.io/slopless/

## How it works

- `topics.yaml` holds the topics and the quality thresholds. Only `enabled: true` topics run.
- `pipeline.py` is the one script: find (YouTube Data API + [HackerTube](https://hackertube.org/data)
  for `hn_boost` topics) → cut the noise → label (Haiku sub-agents) → transcripts or chapter fallback →
  score and pick a clip (Sonnet sub-agents) → select → `clips.json` + `topics.json`.
- `data/videos.json` caches every processed video and its result, so re-runs skip finished videos and
  adding a topic only costs that topic.
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

## Thresholds (defaults in `topics.yaml`)

| filter | value |
|---|---|
| minimum length | 8 min |
| maximum age | 24 months (Parenting: 60) |
| minimum views | 5,000 (1,000 if Hacker News recommended it) |
| minimum like/view ratio | 1.5% (skipped when likes are hidden) |
| candidates scored per topic | top 100 by engagement rank |
| minimum substance | 7 / 10 (+1 for HN-recommended on `hn_boost` topics, or trusted channels) |
| max clips per channel | 5 |
| clips per topic | 50 |

Engagement rank (used to keep the top 100): `log10(views) + 60·likes/views + 200·comments/views (+1 if HN)`.
