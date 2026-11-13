# Clip summary job (run on Haiku)

Each `data/work/summaries/batch_NNN.in.json` lists clips with the exact words spoken in them (`text`, from
the video's captions), plus the video title, channel and the clip's hook.

For every clip write, from the `text` only (never add facts that are not said in it):
- `summary`: 1–2 plain sentences, at most 40 words, saying what the speaker explains or argues in this
  minute. Name the speaker's point, not the topic ("Karpathy argues X because Y", not "This clip is about X").
- `points`: 2–3 short takeaways, each at most 12 words, concrete and specific. Fewer if the clip has fewer.
No hype, no emoji, no "In this clip". Captions are auto-generated and may contain mis-heard words; fix
obvious ones from context, and leave out anything you cannot make sense of.

Write `data/work/summaries/batch_NNN.out.json` (same NNN) containing only:
{"model": "<the model you are running on>", "summaries": {"<clip id>": {"summary": "...", "points": ["...", "..."]}, ...}}
Every clip id in the input must appear. Do not edit any other file.
