# Debate fact-check job, stage 2 (run on Sonnet)

`data/work/debates/check.in.json` lists proposed debates. Each has a question and sides; each side has a short
label, a one-sentence stance, and its clips with `words`: the exact words spoken in the clip (auto-generated
captions, so expect small mis-hearings; clips without captions have empty `words`).

You are the safety check before real people's positions are shown to viewers. For every debate decide, using
ONLY the `words` (never outside knowledge of the speakers):

1. For each side, is the stated stance **supported**: does at least one of that side's clips, in its own
   words, clearly express that position (not merely something near it, not a stronger or weaker version)?
   A side whose clips have no `words` cannot be supported.
2. Is the debate **fair**: do the sides really answer the same question and disagree, and is the question
   neutral (not loaded toward one side)?

Be strict. When in doubt, mark it not supported. A correct "no" is better than a wrong attribution.

Write `data/work/debates/check.out.json` containing only:
{"model": "<the model you are running on>", "verdicts": {"d1": {"fair": true, "sides_supported": [true, true], "note": "<one sentence: what you checked, or why it failed>"}, ...}}
`sides_supported` has one boolean per side, in the order given. Every debate id must appear. Do not edit any
other file.
