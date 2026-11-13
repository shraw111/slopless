# Subject merging job (run on Haiku)

`data/work/subjects/<topic>.in.json` lists a topic's clips (`id` = video id + start second) with the `subject` each
was tagged with, plus its hook. One video can have several clips. Different scorers named the same idea differently ("attention", "self-attention", "attention
mechanism", "q k v"). Merge them.

For every clip give a `group`: a short lowercase name shared by all clips about the SAME core idea.
- Same idea, different wording or different presenter → same group (all attention-mechanism explainers are
  one group; PPO-vs-GRPO and GRPO training are one group).
- Related but different ideas stay apart ("kv cache" vs "speculative decoding"; "rag chunking" vs
  "rag evaluation"; "evals for pms" vs "llm-as-judge rubrics").

Write `data/work/subjects/<topic>.out.json` containing only:
{"model": "<the model you are running on>", "groups": {"<clip id>": "<group>", ...}}
Use each clip's `id` from the input (e.g. "EWvNQjAaOHw-548"); every id must appear. Do not edit any other file.
