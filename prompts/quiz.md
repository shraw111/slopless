# Recall question job (run on Haiku)

Each `data/work/quiz/batch_NNN.in.json` lists clips with their hook, summary and key points (written from
the clip's transcript). For every clip write one recall question that someone who watched the clip a few
days ago can answer from memory, and its answer.

- `q`: one question, at most 15 words, about the clip's single most useful idea. Ask about the idea, not
  trivia (no "what colour", no "how many minutes"). Good: "Why do classifier-free guidance models subtract
  the unconditioned direction?" Bad: "What did the video say?"
- `a`: the answer in at most 25 words, using only what the summary and points say.

Write `data/work/quiz/batch_NNN.out.json` (same NNN) containing only:
{"model": "<the model you are running on>", "quiz": {"<clip id>": {"q": "...", "a": "..."}, ...}}
Every clip id in the input must appear. Do not edit any other file.
