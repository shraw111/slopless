# Subject merging job (run on Haiku)

`data/work/subjects/<topic>.in.json` lists a topic's clips with the `subject` each was tagged with, plus its
hook. Different scorers named the same idea differently ("attention", "self-attention", "attention
mechanism", "q k v"). Merge them.

For every clip give a `group`: a short lowercase name shared by all clips about the SAME core idea.
- Same idea, different wording or different presenter → same group (all attention-mechanism explainers are
  one group; PPO-vs-GRPO and GRPO training are one group).
- Related but different ideas stay apart ("kv cache" vs "speculative decoding"; "rag chunking" vs
  "rag evaluation"; "evals for pms" vs "llm-as-judge rubrics").

Write `data/work/subjects/<topic>.out.json` containing only:
{"model": "<the model you are running on>", "groups": {"<vid>": "<group>", ...}}
Every vid in the input must appear. Do not edit any other file.
