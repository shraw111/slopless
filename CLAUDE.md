# signal-shorts: runbook for Claude Code

When the user says **"Run the pipeline for new topics"** (or "run the pipeline"), follow these steps in order.
Pipeline data lives in the PRIVATE repo `shraw111/slopless-data`, cloned at `../slopless-data` (attach it with
`add_repo` and clone it there if missing). Paths below like `data/...` are inside that repo; commit and push data
changes THERE, never in this public repo (it ignores `data/`). Only `clips.json` and `topics.json` are public.
Never commit API keys. `YOUTUBE_API_KEY` must be an environment variable; if it is missing, stop and say so.

Models: you (the orchestrator) plan and review. Sub-agents run with the model set explicitly:
**Haiku** for labeling (step 3), **Sonnet** for scoring (step 5). Afterwards, report which model each
sub-agent actually ran on (check the `model` field the agents wrote and the session's event log).

1. `python pipeline.py status` and `python pipeline.py queries`.
   For each enabled topic with no queries, write ~20 search queries from its `covers` (specific, aimed at
   long-form explainers/talks, avoiding its `exclude`) into `data/queries/<id>.json` as
   `{"approved": false, "queries": [...]}`. **Show them to the user and wait.** On approval run
   `python pipeline.py approve-queries <id>`. Topics with `queries:` in topics.yaml are already approved.
2. For `hn_boost` topics, `find` downloads the zip from hackertube.org/data and unzips it to
   `data/hackertube/hackertube-data/`. **Read `DATA.md` there first** (stances, `shelf_life`, duplicate
   uploads, what's missing, ODC-By license) and check the script's rules still match it, then the script
   pulls each topic's matches from `videos.jsonl`.
   `python pipeline.py find` — YouTube search (English, embeddable, `max_age_months`), stats, channel
   subscribers, HackerTube matches for `hn_boost` topics, then the noise filters from topics.yaml
   (`min_views`, `min_views_hn`, `min_like_ratio`, `min_minutes`). Videos already in `data/videos.json` are
   skipped, so only new topics cost API quota (~100 units per query page).
   **Shorts** (topics with `shorts: true`; opt in, off by default): `python pipeline.py find --shorts --topic <id>` searches
   Shorts (`videoDuration=short`) with the topic's approved queries (~100 units each). They go through steps 3 and 5 like the
   rest (no transcript or heatmap; Sonnet judges title/description, strict, see `prompts/score.md`). One Short = one clip,
   at most `max_shorts_per_topic` per topic, bar `min_substance_short`. Show the user the Shorts before publishing.
3. `python pipeline.py label-prep`, then spawn Haiku sub-agents (`model: "haiku"`), each given
   `prompts/label.md` and a few batch files from `data/work/labels/`. Then `python pipeline.py label-apply`.
4. `python pipeline.py transcripts` — tries timestamped transcripts; on failure (YouTube often blocks cloud
   IPs) falls back to chapter timestamps in the description. Then `python pipeline.py heatmap` reads each
   candidate's YouTube "Most replayed" heatmap from the watch page (not the Data API; 3 s between requests,
   stops on 429s; re-run later to fill gaps). Videos with only a heatmap become usable too. Report counts.
5. `python pipeline.py score-prep --topic <id> --limit 15`, then spawn Sonnet sub-agents (`model: "sonnet"`),
   each given `prompts/score.md` and ~5 files from `data/work/score/`. Then `python pipeline.py score-apply`
   and `python pipeline.py select`. Repeat until the topic has 10 published clips.
   Then `python pipeline.py subjects-prep`, one Haiku sub-agent with `prompts/subjects.md`, and
   `python pipeline.py subjects-apply` so `max_clips_per_subject` can stop near-identical clips.
   To re-score everything after a prompt change, use `score-prep --rescore`.
6. **STOP for new topics** (state `phase: preview` in `data/state.json`): show the user the 10 clips
   (hook, channel, title, substance, link with `&t=<start>`) and wait. On approval run
   `python pipeline.py promote <id>` and continue steps 5 until `clips_per_topic` or candidates run out.
7. Summaries: `python pipeline.py select`, then `python pipeline.py summaries-prep`, Haiku sub-agents with
   `prompts/summaries.md` (one per batch file in `data/work/summaries/`), and `python pipeline.py summaries-apply`.
   Only clips with a transcript get a summary; the others keep their one-line "why".
   Levels: `levels-prep`, Haiku with `prompts/levels.md` (one agent per batch file), `levels-apply`, then `select`
   (the feed's Level chip filters on `level`).
   Paths: `paths-prep`, one Sonnet agent per topic with `prompts/paths.md`, `paths-apply` → `paths.json`.
   Debates: `debates-prep`, Sonnet with `prompts/debates.md`, then `debates-check-prep` and a SECOND Sonnet pass
   with `prompts/debates-check.md` (it judges only the words actually spoken; never loosen it). If a side fails
   because its stance mixes claims, reword that side to the one claim every clip supports and re-check, as
   was done for "next-word prediction"; never skip the check. Then `debates-apply` → `debates.json`.
   Paths and debates refer to clip ids (`<video>-<start>`), so rerun them after clips are re-cut.
8. `python pipeline.py select`, commit `clips.json` and `topics.json` here and push to `main`; commit
   `data/` in `../slopless-data` and push it there (GitHub Pages deploys from `main`).
9. Summarize: clips per topic, thresholds used (from topics.yaml), API units (`data/usage.json`) and
   sub-agent models.

## Weekly refresh

When the prompt says **"Run the weekly refresh"** (a scheduled task sends it every week), do this without
stopping for approval. Topics in `phase: preview` (new topics) are skipped: those still need the user.
1. If the repos aren't in the session, attach `shraw111/slopless` and `shraw111/slopless-data` with push access
   and clone them side by side. Work on `main` in both.
2. `python pipeline.py find --refresh` for each topic in `phase: full` (`--topic <id>`). The YouTube key is a
   network secret on the environment (header X-Goog-Api-Key); never ask for it in chat, never commit it.
3. Steps 3–5 and 7 above for the new videos only (no `--rescore`): label (Haiku), transcripts + heatmap,
   score (Sonnet; ~5 files per agent, larger transcripts fewer), subjects (Haiku), summaries (Haiku).
   Transcripts are usually blocked from cloud servers; new clips then use chapters (bar 6) until the user
   runs `python pipeline.py transcripts --retry` on their own computer.
4. Bad cuts: list open GitHub issues on `shraw111/slopless` titled "Bad cuts" (sent from the feed's
   History → Flagged tab). Save each issue body to a file, `python pipeline.py flags-apply <file>`, then
   `score-prep --flagged` + Sonnet + `score-apply` to re-cut those videos, then `quiz-prep`/`summaries-prep`
   for the new cuts. Comment on each issue with what changed and close it.
5. Recall questions: `python pipeline.py quiz-prep`, Haiku with `prompts/quiz.md`, `python pipeline.py quiz-apply`.
   New clips also need levels (`levels-prep` / Haiku / `levels-apply`). Rerun paths and debates (step 7) when
   10 or more clips were added or any were re-cut; otherwise leave them.
6. `python pipeline.py select`, commit `clips.json` and `topics.json` here and `data/` in `../slopless-data`
   with a message like "Weekly refresh: +N clips", and push both to `main`.
7. End with a short report: new videos found, clips added per topic, API units used, sub-agent models.
   If nothing new qualified, say so and change nothing.
