# X post context job (run on Haiku)

`data/work/x/batch_000.in.json` lists hand-picked X (Twitter) text posts from people the viewer trusts, each with
`author`, `handle`, `text` and a `topic`. In the feed each post is shown next to ONE line of yours that answers,
in order: (1) **who** is posting and why that matters (only what the text itself shows or the handle makes obvious,
never invent credentials), (2) **why it is worth reading**: the claim, lesson or question, concretely.

Rules:
- 20-45 words, at most 2 sentences, plain language, explain any jargon. The card already shows the author's name and handle above your line, so do not repeat the handle; say what makes them worth hearing from (only if the text shows it) and then the point. Refer to them by surname, never by a guessed pronoun.
- Use only `author`, `handle` and `text`. Do not add facts, numbers, dates or affiliations that are not there.
- Do not quote the post at length (a short phrase is fine) and do not repeat it word for word.
- No hype, no emoji, no "This post". If the text is a thread opener, say it opens a thread.

Write `data/work/x/batch_000.out.json` containing only:
{"model": "<the model you are running on>", "context": {"<post id>": "<line>", ...}}
Every post id in the input must appear. Do not edit any other file.
