# Scoring + clip picking job (run on Sonnet)

Each `data/work/score/<vid>.in.md` holds a topic definition and one video, with a timestamped transcript
(`[seconds] text`, ~15 s per line) or, when none was available, its chapter list and/or description. Most
files also have a MOST REPLAYED section: the slices of the video real viewers replayed most (YouTube's
heatmap, first minute excluded), with scores from 0 to 1.

Judge the WHOLE video for the topic, then pick its single best stand-alone clip.

substance (1–10), for this topic. Use this scale the same way every time; most videos land at 4–6, and a 7
must be something a working practitioner would be glad to have watched:
- 9–10: expert-level insight or a demo a practitioner would bookmark; clear, specific, non-obvious.
- 7–8: solid, specific explanation or lesson; worth a minute of a smart person's time.
- 4–6: correct but generic, shallow, padded or mostly opinion.
- 1–3: hype, news recap, listicle, sales pitch, off-topic, or matches the topic's EXCLUDE list.
- Beginner "what is X" overviews, tool tutorials that mostly click through a UI, course chapters that only
  restate common definitions, and long courses padded with setup score at most 5 unless the explanation is
  unusually clear or original (e.g. 3Blue1Brown-level visual intuition).
- Talks and interviews with first-hand experience (a researcher on their own work, a team on a decision
  they made) score higher than second-hand summaries of the same idea.

The clip (end_sec − start_sec between 60 and 90, inclusive):
- Must stand alone: someone who has not seen the video understands it. It starts at the beginning of a
  thought (not mid-sentence) and ends after the point lands.
- It must match the topic's GOOD CLIP description.
- Never an intro, channel/sponsor read, "like and subscribe", agenda/outline, Q&A logistics or outro.
- Use MOST REPLAYED to find where the best minute is: prefer the highest-replayed slice whose content fits
  GOOD CLIP (judge content from the transcript or the chapter covering it). Skip peaks that are likely
  sponsor reads, intros, giveaways or a visual gag. A slice is coarse (often 30–120 s), so align the start
  to a nearby chapter boundary or sentence start inside or just before the peak.
- With chapters only (no heatmap): choose the chapter that best fits GOOD CLIP and start at its timestamp
  (or a little after, if the chapter likely opens with setup).
- Without a transcript, lower substance by 1 for uncertainty. With neither chapters nor transcript, judge
  substance from the title and description only and be strict (max 7).
- end_sec must not exceed the video length.

subject: the core idea of the clip as a 1–4 word lowercase noun phrase, as generic as possible so clips on
the same idea share it, e.g. "self-attention", "grpo", "kv cache", "rag chunking", "evals for pms",
"ai pricing". Used to stop the feed repeating itself.
hook: under 12 words, plain and specific, says what the viewer will get. No clickbait, no emoji, no
"You won't believe". Example: "Why RAG fails on tables, and the fix".
why: one line on why this clip is worth watching.

Write `data/work/score/<vid>.out.json` containing only:
{"substance": 8, "start_sec": 754, "end_sec": 832, "hook": "...", "topic": "<topic id>", "why": "...",
 "subject": "self-attention", "used_heatmap": true, "model": "<the model you are running on>"}
Use the topic id from the input file. Do not edit any other file.
