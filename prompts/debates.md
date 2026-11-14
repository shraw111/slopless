# Debate finder job, stage 1 (run on Sonnet)

`data/work/debates/propose.in.json` lists every clip: id, topic, source (channel and video), hook, `about` (a
summary of what is said), key points, and whether it has a transcript. Find **real disagreements**: a question
on which two or more speakers in these clips hold clearly different positions, so a viewer can watch one side,
then the other.

A debate is only valid when:
- it is a genuine disagreement about the same question (for example "Can scaling language models alone lead to
  general intelligence?"), not two speakers who talk about the same subject in agreement or about different
  things;
- each side is backed by 1 to 3 clips whose `about` / key points state that position clearly. Prefer clips
  with `has_transcript: true`; every side needs at least one;
- each side's position is stated using only what the clips' `about` and key points say. Never add what a
  person "probably thinks", never use outside knowledge of their views, and never turn a nuanced remark into a
  stronger claim;
- the sides come from different clips (usually different speakers or videos).

Return only debates you are confident in: 3 to 8 is plenty, fewer (even zero) if the material does not have
real disagreements. Do not force one. Do not include two debates on the same question.

Write `data/work/debates/propose.out.json` containing only:
{"model": "<the model you are running on>", "debates": [
  {"id": "d1", "question": "<one neutral question, under 16 words>",
   "differ": "<one sentence on what the sides actually disagree about>",
   "sides": [{"label": "<short stance, under 9 words>", "stance": "<one sentence, only what the clips say>", "clips": ["<clip id>", ...]},
             {"label": "...", "stance": "...", "clips": ["..."]}]}]}
Use ids d1, d2, ... Every clip id must be copied exactly from the input. Do not edit any other file.
