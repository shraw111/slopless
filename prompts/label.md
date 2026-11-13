# Labeling job (run on Haiku)

You sort YouTube videos into topics. For each batch file `data/work/labels/batch_NNN.in.json` you are given:
- `topics`: every enabled topic with `id`, `name`, `covers` (what belongs) and `exclude` (what does not).
- `videos`: title, channel, length, tags and the start of the description.

For every video pick exactly ONE topic id, or `"none"`:
- Pick a topic only if the video's main subject is in that topic's `covers` AND it is not one of its `exclude` kinds.
- `"none"` for news recaps, hype, listicles ("top 10 tools"), sponsored product walkthroughs, reaction videos,
  shorts compilations, course ads, or anything off-topic. When unsure between a topic and "none", choose "none".
- If two topics fit, pick the one the video is mostly about.

Write `data/work/labels/batch_NNN.out.json` (same NNN) containing only:
{"model": "<the model you are running on>", "labels": {"<vid>": "<topic id or none>", ...}}
Every vid in the input must appear. Do not edit any other file.
