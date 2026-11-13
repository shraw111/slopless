# signal-shorts: runbook for Claude Code

When the user says **"Run the pipeline for new topics"** (or "run the pipeline"), follow these steps in order.
Never commit API keys. `YOUTUBE_API_KEY` must be an environment variable; if it is missing, stop and say so.

Models: you (the orchestrator) plan and review. Sub-agents run with the model set explicitly:
**Haiku** for labeling (step 3), **Sonnet** for scoring (step 5). Afterwards, report which model each
sub-agent actually ran on (check the `model` field the agents wrote and the session's event log).

1. `python pipeline.py status` and `python pipeline.py queries`.
   For each enabled topic with no queries, write ~20 search queries from its `covers` (specific, aimed at
   long-form explainers/talks, avoiding its `exclude`) into `data/queries/<id>.json` as
   `{"approved": false, "queries": [...]}`. **Show them to the user and wait.** On approval run
   `python pipeline.py approve-queries <id>`. Topics with `queries:` in topics.yaml are already approved.
2. `python pipeline.py find` — YouTube search (English, embeddable, `max_age_months`), stats, channel
   subscribers, HackerTube matches for `hn_boost` topics, then the noise filters from topics.yaml
   (`min_views`, `min_views_hn`, `min_like_ratio`, `min_minutes`). Videos already in `data/videos.json` are
   skipped, so only new topics cost API quota (~100 units per query page).
3. `python pipeline.py label-prep`, then spawn Haiku sub-agents (`model: "haiku"`), each given
   `prompts/label.md` and a few batch files from `data/work/labels/`. Then `python pipeline.py label-apply`.
4. `python pipeline.py transcripts` — tries timestamped transcripts; on failure (YouTube often blocks cloud
   IPs) falls back to chapter timestamps in the description. Report how many used each.
5. `python pipeline.py score-prep --topic <id> --limit 15`, then spawn Sonnet sub-agents (`model: "sonnet"`),
   each given `prompts/score.md` and ~5 files from `data/work/score/`. Then `python pipeline.py score-apply`
   and `python pipeline.py select`. Repeat until the topic has 10 published clips.
6. **STOP for new topics** (state `phase: preview` in `data/state.json`): show the user the 10 clips
   (hook, channel, title, substance, link with `&t=<start>`) and wait. On approval run
   `python pipeline.py promote <id>` and continue steps 5 until `clips_per_topic` or candidates run out.
7. `python pipeline.py select`, commit `clips.json`, `topics.json` and `data/` (not `data/work/`,
   `data/hackertube/`), push, and merge to `main` (GitHub Pages deploys from `main`).
8. Summarize: clips per topic, thresholds used (from topics.yaml), API units (`data/usage.json`) and
   sub-agent models.
