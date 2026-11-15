# Context line job (run on Haiku)

Each `data/work/context/batch_NNN.in.json` lists clips from a feed of 60-90 second excerpts of longer YouTube
talks. A viewer scrolling past sees only the hook and has no idea what the video is. For every clip write ONE
`context` line that answers two things in order:
1. **What this is**: who is speaking and the setting (the talk, the experiment, the product), in plain words.
2. **Why it is worth the minute**: what the viewer will see or learn here, concrete, not "interesting".

Rules:
- 20-45 words, at most 2 sentences. Plain language; explain any jargon or name a stranger would not know.
- Use ONLY `video_title`, `channel`, `video_description`, `hook`, `why`, `summary` and `spoken`. Never add a fact that
  is not in them. If the speaker is unknown, say "a talk on ..." instead of guessing a name.
- Do not repeat the hook word for word; the hook is already shown above it. No hype, no emoji, no "In this clip",
  no "This video".
- Example: hook "Two of four features in 2.5 hours: the honest verdict" ->
  "Rust developer Jon Gjengset let an AI agent build four real features in a codebase, then judges how fast it was and
  whether the tests it wrote were worth having."

Write `data/work/context/batch_NNN.out.json` (same NNN) containing only:
{"model": "<the model you are running on>", "context": {"<clip id>": "<line>", ...}}
Every clip id in the input must appear. Do not edit any other file.
