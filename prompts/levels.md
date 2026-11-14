# Level tagging job (run on Haiku)

Each `data/work/levels/batch_NNN.in.json` lists clips (id, subject, hook, `about` = a summary of what is said,
key points, channel and source video). Give every clip one level, judged by what a viewer must ALREADY know to
follow it, not by how impressive the speaker is:

- `intro`: assumes no background in the subject. Explains from first principles, defines its terms, uses
  analogies or visuals. A smart newcomer can follow it. Examples: "what a token is", "what an AI agent is".
- `intermediate`: assumes the basics and the vocabulary. The viewer has used or built something with this.
  Covers how and why things work, practical decisions, common pitfalls. Examples: choosing a chunking
  strategy, designing evals, how sampling settings change output.
- `advanced`: assumes working depth: implementation details, research-level ideas, maths, or trade-offs at
  scale. A practitioner or researcher would get the most from it. Examples: why GRPO drops the value model,
  interpretability circuits, scaling-law arguments.

Rules: judge from the text given; when torn between two levels pick the lower one if the clip defines its
terms, the higher one if it uses them without explaining. Beginner "what is X" overviews are `intro` even when
the video is long. Do not use any other value.

Write `data/work/levels/batch_NNN.out.json` (same NNN) containing only:
{"model": "<the model you are running on>", "levels": {"<clip id>": "intro" | "intermediate" | "advanced", ...}}
Every clip id in the input must appear. Do not edit any other file.
