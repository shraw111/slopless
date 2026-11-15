# X post job (run on Sonnet for auto-found posts; Haiku is fine when every post is hand-picked)

`data/work/x/batch_000.in.json` lists hand-picked X (Twitter) text posts from people the viewer trusts, each with
`author`, `handle`, `text` and a `topic`. In the feed each post is shown next to ONE line of yours that answers,
in order: (1) **who** is posting and why that matters (only what the text itself shows or the handle makes obvious,
never invent credentials), (2) **why it is worth reading**: the claim, lesson or question, concretely.

Rules:
- 20-45 words, at most 2 sentences, plain language, explain any jargon. The card already shows the author's name and handle above your line, so do not repeat the handle; say what makes them worth hearing from (only if the text shows it) and then the point. Refer to them by surname, never by a guessed pronoun.
- Use only `author`, `handle` and `text`. Do not add facts, numbers, dates or affiliations that are not there.
- Do not quote the post at length (a short phrase is fine) and do not repeat it word for word.
- No hype, no emoji, no "This post". If the text is a thread opener, say it opens a thread.

Posts with `"needs_substance": true` were found automatically, not picked by the viewer, so also judge them strictly
from the text alone (never from the author's fame): `substance` 1-10 = does it teach something, make a concrete
checkable claim, or share a first-hand result a practitioner could act on? 8-10 rare. Give 4 or less to hype,
announcements, vague takes, promotion, engagement bait ("thoughts?"), quote-dunks, jokes and bare links.
Still write the `context` line for every post, but a post you would score under 7 will be dropped.

Write `data/work/x/batch_000.out.json` containing only:
{"model": "<the model you are running on>", "context": {"<post id>": "<line>", ...},
 "substance": {"<post id>": <1-10>, ...}}   (substance only for posts with needs_substance true)
Every post id in the input must appear. Do not edit any other file.
