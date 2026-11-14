# Learning path job (run on Sonnet)

`data/work/paths/<topic>.in.json` lists every clip of one topic: id, hook, `about` (what is said), subject,
level (intro / intermediate / advanced), channel, source video and length. Build **learning paths** from them:
short ordered sequences that take a viewer from the fundamentals of one idea to a confident understanding.

Rules for a path:
- 3 to 8 steps, each step a clip `id` copied exactly from the input. Never invent an id.
- Ordered so every step builds on the ones before it. Start with the clip that needs the least background.
  Levels should generally rise (intro, then intermediate, then advanced) but a path need not contain all three.
- One clear goal a viewer would recognise, e.g. "Understand how a transformer reads and generates text" or
  "Ship a reliable AI feature: evals, cost and pricing". The `goal` is one sentence saying what the viewer can
  do or explain after the last step.
- Mix sources when the quality is there: prefer several channels over one, but never pick a weaker clip just
  for variety.
- A clip may appear in at most two paths. Do not pad: if a goal has only 3 good clips, the path has 3 steps.
- Judge fit from `about`, subject and level only; do not claim a clip says something its `about` does not say.

Write 5 to 8 paths per topic (fewer if the material cannot support them). Prefer paths that cover different
parts of the topic over several paths on the same idea.

Write `data/work/paths/<topic>.out.json` (same topic id as the input file name) containing only:
{"model": "<the model you are running on>", "paths": [{"title": "...", "goal": "...", "steps": ["<clip id>", ...]}, ...]}
Title: under 9 words, plain, no hype. Do not edit any other file.
