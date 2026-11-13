#!/usr/bin/env python3
"""signal-shorts pipeline. Reads topics.yaml and runs enabled topics only.

Deterministic steps run here. The two judgement steps (Haiku labels, Sonnet scores) are done by
Claude Code sub-agents that read the work files this script writes and write JSON back.
See CLAUDE.md for the full run order.

  python pipeline.py status
  python pipeline.py queries                  # show stored/approved queries per topic
  python pipeline.py approve-queries TOPIC    # mark a topic's queries as approved
  python pipeline.py find [--topic T]         # YouTube search + HackerTube, stats, filters
  python pipeline.py label-prep               # write Haiku batches for unlabeled videos
  python pipeline.py label-apply              # merge Haiku outputs into the cache
  python pipeline.py transcripts [--topic T] [--limit N]
  python pipeline.py heatmap [--topic T]      # YouTube "Most replayed" peaks per candidate
  python pipeline.py score-prep [--topic T] [--limit N]
  python pipeline.py score-apply
  python pipeline.py subjects-prep / subjects-apply   # Haiku merges near-identical clip subjects
  python pipeline.py select [--preview]       # write clips.json + topics.json for the feed
"""
import argparse, datetime as dt, gzip, html, json, math, os, re, sys, zipfile
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CACHE = DATA / "videos.json"          # every processed video id and its results
STATE = DATA / "state.json"           # per-topic progress (preview / full)
QUERIES = DATA / "queries"            # data/queries/<topic>.json
WORK = DATA / "work"                  # sub-agent inputs/outputs (labels/, score/)
TRANSCRIPTS = DATA / "transcripts"    # data/transcripts/<vid>.json.gz
HT_DIR = DATA / "hackertube"          # downloaded HackerTube export (git-ignored)
YT = "https://www.googleapis.com/youtube/v3"
NOW = dt.datetime.now(dt.timezone.utc)

STOP = set("""a an and or the of to in on for with how what why when is are be by from as at it its this that
into about your you we our can do does using use used vs versus explained intro introduction talk talks
work works working research build building product products""".split())


# ---------------------------------------------------------------- config & cache
def load_config():
    cfg = yaml.safe_load((ROOT / "topics.yaml").read_text())
    d = cfg.get("defaults", {})
    topics = []
    for t in cfg.get("topics", []):
        merged = {**d, **t}
        merged.setdefault("hn_boost", False)
        merged.setdefault("trusted_channels", [])
        topics.append(merged)
    return d, topics


def enabled_topics(only=None):
    _, topics = load_config()
    ts = [t for t in topics if t.get("enabled")]
    if only:
        ts = [t for t in ts if t["id"] == only]
        if not ts:
            sys.exit(f"topic '{only}' is not enabled in topics.yaml")
    return ts


def jload(p, default):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def jsave(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def load_cache():
    return jload(CACHE, {})


def save_cache(c):
    jsave(CACHE, c)


# ---------------------------------------------------------------- YouTube Data API
def yt(endpoint, **params):
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        sys.exit("YOUTUBE_API_KEY is not set. Add it as an environment variable (never commit it).")
    params["key"] = key
    r = requests.get(f"{YT}/{endpoint}", params=params, timeout=30)
    if r.status_code != 200:
        sys.exit(f"YouTube API {endpoint} failed: {r.status_code} {r.text[:300]}")
    usage = jload(DATA / "usage.json", {})
    cost = 100 if endpoint == "search" else 1
    day = NOW.strftime("%Y-%m-%d")
    usage[day] = usage.get(day, 0) + cost
    jsave(DATA / "usage.json", usage)
    return r.json()


def iso_minutes(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    days, h, mi, s = (int(x or 0) for x in m.groups())
    return days * 1440 + h * 60 + mi + s / 60


def months_ago(n):
    return NOW - dt.timedelta(days=int(n * 30.44))


def fetch_details(vids):
    """videos.list + channels.list for ids; returns {vid: info}."""
    out = {}
    vids = list(dict.fromkeys(vids))
    for i in range(0, len(vids), 50):
        res = yt("videos", part="snippet,contentDetails,statistics,status", id=",".join(vids[i:i + 50]),
                 maxResults=50)
        for it in res.get("items", []):
            sn, st, cd = it["snippet"], it.get("statistics", {}), it["contentDetails"]
            out[it["id"]] = {
                "vid": it["id"], "title": html.unescape(sn["title"]), "channel": sn["channelTitle"],
                "channel_id": sn["channelId"], "published": sn["publishedAt"],
                "description": sn.get("description", "")[:5000], "tags": sn.get("tags", [])[:20],
                "lang": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or "",
                "live": sn.get("liveBroadcastContent", "none"),
                "minutes": round(iso_minutes(cd.get("duration")), 1),
                "embeddable": it.get("status", {}).get("embeddable", False),
                "views": int(st.get("viewCount", 0)),
                "likes": int(st["likeCount"]) if "likeCount" in st else None,
                "comments": int(st["commentCount"]) if "commentCount" in st else None,
            }
    chans = list({v["channel_id"] for v in out.values()})
    subs = {}
    for i in range(0, len(chans), 50):
        res = yt("channels", part="statistics", id=",".join(chans[i:i + 50]), maxResults=50)
        for it in res.get("items", []):
            s = it.get("statistics", {})
            subs[it["id"]] = None if s.get("hiddenSubscriberCount") else int(s.get("subscriberCount", 0))
    for v in out.values():
        v["subscribers"] = subs.get(v["channel_id"])
    return out


# ---------------------------------------------------------------- HackerTube
def hackertube():
    """{vid: card} for videos HN recommended, from the HackerTube data export (hackertube.org/data).

    Downloads the export zip, unzips it to data/hackertube/hackertube-data/ and applies the rules in its
    DATA.md (read it before relying on the matches): only rec/strong_rec count as recommendations
    (hn.recommenders > 0), shelf_life "news" is hidden, and duplicate uploads are deduped by normalized
    title, keeping the first (the file is sorted best-scored first). Data is ODC-By: credit HackerTube.
    """
    d = HT_DIR / "hackertube-data"
    if not (d / "videos.jsonl").exists():
        HT_DIR.mkdir(parents=True, exist_ok=True)
        meta = requests.get("https://hackertube.org/api/export", timeout=30).json()
        r = requests.get(f"https://hackertube.org/download/{meta['zip']['name']}", timeout=600)
        r.raise_for_status()
        zpath = HT_DIR / meta["zip"]["name"]
        zpath.write_bytes(r.content)
        with zipfile.ZipFile(zpath) as z:
            for n in z.namelist():  # extract only plain relative paths
                if n.startswith("hackertube-data/") and ".." not in n:
                    z.extract(n, HT_DIR)
        print(f"HackerTube export {meta.get('generated')} unzipped -> {d}; read {d / 'DATA.md'} first")
    cards, titles = {}, set()
    for line in (d / "videos.jsonl").open():
        v = json.loads(line)
        if v.get("hn", {}).get("recommenders", 0) == 0 or v.get("shelf_life") == "news":
            continue
        if v.get("content_type") in ("comedy", "music"):
            continue
        norm = re.sub(r"[^a-z0-9]+", " ", v["title"].lower()).strip()
        if norm in titles:
            continue
        titles.add(norm)
        cards[v["vid"]] = v
    return cards


def topic_keywords(t):
    if t.get("hn_keywords"):
        return [k.lower() for k in t["hn_keywords"]]
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]+", f"{t['name']} {t['covers']}".lower())
    kws = {w for w in words if w not in STOP and len(w) >= 2}
    kws |= {w.rstrip("s") for w in kws if len(w) > 4}
    return sorted(kws)


def hn_matches(t, cards):
    """A topic's matches in videos.jsonl: at least 2 distinct topic keywords across the title, HN summary,
    why_hn, primary topic, tags and category names. Haiku labeling then confirms or rejects each one."""
    kws = topic_keywords(t)
    pat = re.compile(r"\b(" + "|".join(map(re.escape, kws)) + r")s?\b")
    out = []
    for vid, v in cards.items():
        text = " ".join([v["title"], v.get("summary", ""), v.get("why_hn", ""), v.get("primary_topic", ""),
                         " ".join(v.get("tags", [])), " ".join(c["name"] for c in v.get("categories", []))]).lower()
        if len(set(pat.findall(text))) >= 2:
            out.append(vid)
    return out


# ---------------------------------------------------------------- 1. find + 2. filter
def cmd_queries(args):
    for t in enabled_topics(args.topic):
        q = jload(QUERIES / f"{t['id']}.json", None)
        if t.get("queries"):
            print(f"## {t['id']}: {len(t['queries'])} queries from topics.yaml (approved)")
        elif q:
            print(f"## {t['id']}: {len(q['queries'])} generated queries, approved={q['approved']}")
            for s in q["queries"]:
                print("  -", s)
        else:
            print(f"## {t['id']}: NO QUERIES. Write ~20 from 'covers' into data/queries/{t['id']}.json "
                  '({"approved": false, "queries": [...]}) and show them to the user.')


def cmd_approve(args):
    p = QUERIES / f"{args.topic}.json"
    q = jload(p, None) or sys.exit(f"no {p}")
    q["approved"] = True
    q["approved_at"] = NOW.isoformat(timespec="seconds")
    jsave(p, q)
    print(f"approved {len(q['queries'])} queries for {args.topic}")


def topic_queries(t):
    if t.get("queries"):
        return t["queries"]
    q = jload(QUERIES / f"{t['id']}.json", None)
    if not q:
        sys.exit(f"{t['id']}: no queries yet (run `pipeline.py queries`).")
    if not q.get("approved"):
        sys.exit(f"{t['id']}: queries not approved yet. Show them to the user, then `approve-queries {t['id']}`.")
    return q["queries"]


def passes(v, t, hn):
    """Return None if the video passes the config + noise filters, else the reason it was dropped."""
    if not v.get("embeddable"):
        return "not embeddable"
    if v.get("live") != "none":
        return "live/upcoming"
    if v["lang"] and not v["lang"].lower().startswith("en"):
        return "not English"
    if v["minutes"] < t["min_minutes"]:
        return "too short"
    if dt.datetime.fromisoformat(v["published"].replace("Z", "+00:00")) < months_ago(t["max_age_months"]):
        return "too old"
    if v["views"] < (t["min_views_hn"] if hn else t["min_views"]):
        return "low views"
    if v["likes"] is not None and v["views"] and v["likes"] / v["views"] < t["min_like_ratio"]:
        return "weak like ratio"
    return None


def rank(v):
    """Pre-score ranking used to keep the top N per topic: engagement quality over raw reach."""
    views = max(v["views"], 1)
    lr = (v["likes"] or 0) / views
    cr = (v["comments"] or 0) / views
    return round(math.log10(views) + 60 * min(lr, 0.1) + 200 * min(cr, 0.01) + (1.0 if v.get("hn") else 0), 3)


def cmd_find(args):
    cache = load_cache()
    cards = None
    for t in enabled_topics(args.topic):
        qfile = QUERIES / f"{t['id']}.json"
        qdata = jload(qfile, {})
        ran = set(qdata.get("ran", []))
        queries = [q for q in topic_queries(t) if q not in ran]  # each query costs 100 units: run it once
        if not queries:
            print(f"{t['id']}: all queries already ran")
            continue
        after = months_ago(t["max_age_months"]).strftime("%Y-%m-%dT%H:%M:%SZ")
        found = {}
        for q in queries:
            token = None
            for _ in range(int(t.get("search_pages", 1))):
                res = yt("search", part="id", q=q, type="video", maxResults=50, order="relevance",
                         relevanceLanguage="en", videoEmbeddable="true", publishedAfter=after,
                         safeSearch="moderate", **({"pageToken": token} if token else {}))
                for it in res.get("items", []):
                    found.setdefault(it["id"]["videoId"], []).append(q)
                token = res.get("nextPageToken")
                if not token:
                    break
        hn_ids = []
        if t.get("hn_boost"):
            cards = cards or hackertube()
            hn_ids = hn_matches(t, cards)
        if qdata:
            qdata["ran"] = sorted(ran | set(queries))
            jsave(qfile, qdata)
        new = [v for v in set(found) | set(hn_ids) if v not in cache]
        details = fetch_details(new) if new else {}
        kept = dropped = 0
        reasons = {}
        for vid in set(found) | set(hn_ids):
            if vid in cache:
                c = cache[vid]
                c.setdefault("found_for", [])
                if t["id"] not in c["found_for"]:
                    c["found_for"].append(t["id"])
                continue
            v = details.get(vid)
            if not v:
                continue
            v["hn"] = bool(cards) and vid in cards
            if v["hn"]:
                v["hn_why"] = cards[vid].get("why_hn", "")
            v["queries"] = found.get(vid, [])
            v["found_for"] = [t["id"]]
            v["found_at"] = NOW.isoformat(timespec="seconds")
            why = passes(v, t, v["hn"])
            v["status"] = "candidate" if why is None else "dropped"
            v["drop_reason"] = why
            v["rank"] = rank(v)
            if why:
                v.pop("description", None)
            reasons[why or "kept"] = reasons.get(why or "kept", 0) + 1
            cache[vid] = v
        save_cache(cache)
        print(f"{t['id']}: {len(queries)} queries, {len(found)} search hits, {len(hn_ids)} HackerTube matches, "
              f"{len(new)} new -> {reasons}")


# ---------------------------------------------------------------- 2b. Haiku labels
LABEL_BATCH = 40


def topics_brief():
    return [{k: t.get(k) for k in ("id", "name", "covers", "exclude")} for t in enabled_topics()]


def cmd_label_prep(args):
    cache = load_cache()
    todo = [v for v in cache.values() if v["status"] == "candidate" and "label" not in v]
    out = WORK / "labels"
    for f in list(out.glob("batch_*.in.json")) + list(out.glob("batch_*.out.json")):
        f.unlink()  # stale outputs from an earlier run must never be re-applied
    for i in range(0, len(todo), LABEL_BATCH):
        items = [{"vid": v["vid"], "title": v["title"], "channel": v["channel"], "minutes": v["minutes"],
                  "tags": v["tags"][:8], "description": v.get("description", "")[:400]}
                 for v in todo[i:i + LABEL_BATCH]]
        jsave(out / f"batch_{i // LABEL_BATCH:03d}.in.json", {"topics": topics_brief(), "videos": items})
    print(f"{len(todo)} videos to label in {math.ceil(len(todo) / LABEL_BATCH)} batches -> {out}")


def cmd_label_apply(args):
    cache = load_cache()
    ids = {t["id"] for t in enabled_topics()} | {"none"}
    n = bad = 0
    for f in sorted((WORK / "labels").glob("batch_*.out.json")):
        res = json.loads(f.read_text())
        model = res.get("model", "haiku")
        for vid, lab in res["labels"].items():
            if vid in cache and lab in ids:
                cache[vid]["label"] = {"topic": lab, "model": model, "at": NOW.isoformat(timespec="seconds")}
                n += 1
            else:
                bad += 1
    save_cache(cache)
    print(f"applied {n} labels ({bad} invalid)")
    for t in enabled_topics():
        print(f"  {t['id']}: {len(top_candidates(cache, t))} in top {t['top_n']}")


def top_candidates(cache, t):
    c = [v for v in cache.values() if v["status"] == "candidate" and v.get("label", {}).get("topic") == t["id"]]
    return sorted(c, key=lambda v: -v["rank"])[: t["top_n"]]


# ---------------------------------------------------------------- 3a. transcripts / chapters
CHAPTER = re.compile(r"^\s*[\(\[]?((?:\d{1,2}:)?\d{1,2}:\d{2})[\)\]]?\s*[-–—:|]?\s*(.+)$")


def to_sec(ts):
    p = [int(x) for x in ts.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def chapters(desc):
    ch = [(to_sec(m.group(1)), m.group(2).strip()) for line in (desc or "").splitlines()
          if (m := CHAPTER.match(line))]
    # YouTube's rule: at least 3 chapters starting at 0:00, ascending
    if len(ch) >= 3 and ch[0][0] == 0 and all(a[0] < b[0] for a, b in zip(ch, ch[1:])):
        return ch
    return []


def fetch_transcript(vid):
    from youtube_transcript_api import YouTubeTranscriptApi
    t = YouTubeTranscriptApi().fetch(vid, languages=["en", "en-US", "en-GB"])
    return [[round(s.start, 1), s.text] for s in t.snippets]


def cmd_transcripts(args):
    cache = load_cache()
    vids = [v for t in enabled_topics(args.topic) for v in top_candidates(cache, t)
            if v.get("source") is None or (args.retry and v.get("source") != "transcript")][: args.limit or None]
    ok = ch = none = blocked = 0
    for v in vids:
        f = TRANSCRIPTS / f"{v['vid']}.json.gz"
        try:
            if not f.exists():
                if blocked >= 3:  # YouTube is blocking this IP; don't hammer it, use chapters
                    raise RuntimeError("IpBlocked (skipped)")
                try:
                    seg = fetch_transcript(v["vid"])
                    blocked = 0
                except Exception as e:
                    blocked += "Blocked" in type(e).__name__
                    raise
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(gzip.compress(json.dumps(seg).encode()))
            v["source"] = "transcript"
            v.pop("transcript_error", None)
            v.pop("result", None) if args.retry else None  # re-score with the real transcript
            ok += 1
        except Exception as e:  # IP block, no captions, etc.
            v["transcript_error"] = type(e).__name__
            if v.get("source") in ("chapters", "heatmap"):
                continue  # retry failed; keep the earlier fallback
            if chapters(v.get("description")):
                v["source"] = "chapters"
                ch += 1
            else:
                v["source"] = "none"
                none += 1
    save_cache(cache)
    print(f"{len(vids)} videos: {ok} transcripts, {ch} chapter fallbacks, {none} with neither")


# ---------------------------------------------------------------- 3a'. "Most replayed" heatmap
HEAT = re.compile(r'"startMillis":"(\d+)","durationMillis":"(\d+)","intensityScoreNormalized":([\d.eE-]+)')


def fetch_heatmap(vid):
    """YouTube's "Most replayed" graph from the public watch page: {"seg": seconds, "scores": [100 floats]}.
    Returns None when the video has no heatmap (too few views). Not part of the Data API."""
    r = requests.get(f"https://www.youtube.com/watch?v={vid}&hl=en", timeout=30,
                     headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.8"})
    r.raise_for_status()
    s = r.text
    if "ytInitialData" not in s:
        raise RuntimeError("Blocked: watch page without player data")
    i = s.find("MARKER_TYPE_HEATMAP")
    if i < 0:
        return None
    m = HEAT.findall(s[i:i + 30000])
    if not m:
        return None
    return {"seg": round(int(m[0][1]) / 1000, 2), "scores": [round(float(c), 3) for _, _, c in m]}


def cmd_heatmap(args):
    import time
    cache = load_cache()
    vids = [v for t in enabled_topics(args.topic) for v in top_candidates(cache, t) if "heatmap" not in v]
    got = missing = blocked = 0
    for v in vids[: args.limit or None]:
        try:
            v["heatmap"] = fetch_heatmap(v["vid"])
            blocked = 0
        except Exception as e:
            blocked += 1
            print(f"  {v['vid']}: {type(e).__name__} {str(e)[:80]}")
            if blocked >= 3:
                print("  3 failures in a row: YouTube is blocking the watch page, stopping")
                break
            continue
        if v.get("heatmap"):
            got += 1
            if v.get("source") in (None, "none"):
                v["source"] = "heatmap"
        else:
            missing += 1
        time.sleep(3)  # be polite: YouTube returns 429 at ~1 req/s
    save_cache(cache)
    print(f"{len(vids)} videos: {got} with a Most-replayed heatmap, {missing} without")


def heat_peaks(v, n=8):
    """Top replayed segments as text, skipping the first minute (everyone replays the start)."""
    h = v.get("heatmap")
    if not h:
        return ""
    seg, sc = h["seg"], h["scores"]
    idx = [i for i in range(len(sc)) if i * seg >= 60]
    top = sorted(idx, key=lambda i: -sc[i])[:n]
    med = sorted(sc)[len(sc) // 2]
    lines = "\n".join(f"[{int(i * seg)}-{int((i + 1) * seg)}] replay {sc[i]:.2f}" for i in sorted(top))
    return (f"\n\nMOST REPLAYED (YouTube viewers' replay heatmap; {len(sc)} slices of {seg:.0f} s, scores 0-1, "
            f"median {med:.2f}; top {len(top)} after the first minute, in time order):\n{lines}")


# ---------------------------------------------------------------- 3b. Sonnet scoring
def max_clips(v, t):
    """How many clips one video may give: one per `minutes_per_clip` of video, at most `max_clips_per_video`.
    Without a transcript the cuts are guesses, so at most one per chapter."""
    n = max(1, min(int(t["max_clips_per_video"]), int(v["minutes"] // t["minutes_per_clip"])))
    if v.get("source") == "chapters":
        n = min(n, max(1, len(chapters(v.get("description")))))
    elif v.get("source") != "transcript":
        n = 1
    return n


def result_clips(r):
    """A video's clips. Older results were a single clip stored in the result itself."""
    return r.get("clips") or [r]

def compact_transcript(seg, window=15):
    """Merge caption snippets into ~15s lines: '[754] text...'."""
    lines, cur, start = [], [], None
    for s, text in seg:
        if start is None:
            start = s
        cur.append(text.replace("\n", " "))
        if s - start >= window:
            lines.append(f"[{int(start)}] {' '.join(cur)}")
            cur, start = [], None
    if cur:
        lines.append(f"[{int(start)}] {' '.join(cur)}")
    return "\n".join(lines)


def cmd_score_prep(args):
    cache = load_cache()
    out = WORK / "score"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.in.md"):
        f.unlink()
    total = 0
    for t in enabled_topics(args.topic):
        n = 0  # --limit applies per topic
        for v in top_candidates(cache, t):
            if ("result" in v and not args.rescore) or v.get("source") in (None, "none"):
                continue
            if t["require_seen_content"] and v["source"] == "heatmap":  # would not be published anyway
                continue
            if args.limit and n >= args.limit:
                break
            if v["source"] == "transcript":
                seg = json.loads(gzip.decompress((TRANSCRIPTS / f"{v['vid']}.json.gz").read_bytes()))
                body = "TIMESTAMPED TRANSCRIPT ([seconds] text):\n" + compact_transcript(seg)
            elif v["source"] == "chapters":
                body = ("NO TRANSCRIPT. CHAPTERS from the description (seconds, title):\n"
                        + "\n".join(f"[{s}] {c}" for s, c in chapters(v["description"]))
                        + "\n\nDESCRIPTION:\n" + v["description"][:2500])
            else:  # heatmap only
                body = "NO TRANSCRIPT, NO CHAPTERS.\n\nDESCRIPTION:\n" + v.get("description", "")[:2500]
            body += heat_peaks(v)
            (out / f"{v['vid']}.in.md").write_text(
                f"TOPIC id: {t['id']}\nTOPIC name: {t['name']}\nCOVERS: {t['covers']}\nEXCLUDE: {t['exclude']}\n"
                f"GOOD CLIP: {t['good_clip']}\n\nVIDEO: {v['title']}\nCHANNEL: {v['channel']}\n"
                f"LENGTH: {v['minutes']} min ({int(v['minutes'] * 60)} s)\nVIDEO ID: {v['vid']}\n"
                f"MAX CLIPS: {max_clips(v, t)}\n\n{body}\n")
            n += 1
            total += 1
    print(f"{total} videos ready to score -> {out} (prompt: prompts/score.md)")


def cmd_score_apply(args):
    cache = load_cache()
    topics = {t["id"]: t for t in enabled_topics()}
    n = bad = 0
    for f in sorted((WORK / "score").glob("*.out.json")):
        r = json.loads(f.read_text())
        vid = f.name.split(".")[0]
        v = cache.get(vid)
        if not v:
            continue
        t = topics.get(v.get("label", {}).get("topic"))
        limit = max_clips(v, t) if t else 1
        good, problems, taken = [], [], []
        for c in result_clips(r)[:limit]:
            try:
                s, e = int(c["start_sec"]), int(c["end_sec"])
                ok = (1 <= int(c["substance"]) <= 10 and 60 <= e - s <= 90 and s >= 0
                      and e <= v["minutes"] * 60 + 1 and len(c["hook"].split()) < 12 and c.get("why"))
                if ok and any(s < b and a < e for a, b in taken):
                    ok = False  # overlaps another clip of this video
            except (KeyError, ValueError, TypeError):
                ok = False
            if ok:
                taken.append((s, e))
                good.append({k: c[k] for k in ("start_sec", "end_sec", "hook", "why", "subject", "substance")
                             if k in c})
            else:
                problems.append(c)
        if not good or "substance" not in r:
            bad += 1
            print(f"  invalid result for {vid}: {r}")
            continue
        for c in problems:
            print(f"  {vid}: dropped one invalid clip {c}")
        res = {"substance": int(r["substance"]), "topic": r.get("topic"), "model": r.get("model"),
               "clips": sorted(good, key=lambda c: -int(c["substance"])), "at": NOW.isoformat(timespec="seconds")}
        if "result" in v:
            v.setdefault("old_results", []).append(v["result"])
        v["result"] = res
        n += 1
        f.unlink()
        (WORK / "score" / f"{vid}.in.md").unlink(missing_ok=True)
    save_cache(cache)
    print(f"applied {n} scores ({bad} invalid, left in place to redo)")


# ---------------------------------------------------------------- 3c. subject groups (Haiku)
def clip_id(vid, c):
    return f"{vid}-{int(c['start_sec'])}"


def cmd_subjects_prep(args):
    """One file per topic listing eligible clips' subjects, for Haiku to merge near-identical ones."""
    cache = load_cache()
    out = WORK / "subjects"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.out.json"):
        f.unlink()
    for t in enabled_topics(args.topic):
        items = [{"id": clip_id(v["vid"], c), "subject": c.get("subject", ""), "hook": c["hook"],
                  "channel": v["channel"]}
                 for v in cache.values() if v.get("result") and v.get("label", {}).get("topic") == t["id"]
                 for c in result_clips(v["result"]) if int(c["substance"]) + 1 >= t["min_substance_no_transcript"]]
        jsave(out / f"{t['id']}.in.json", {"topic": t["name"], "clips": items})
        print(f"{t['id']}: {len(items)} clips -> {out / (t['id'] + '.in.json')} (prompt: prompts/subjects.md)")


def cmd_subjects_apply(args):
    cache = load_cache()
    by_id = {clip_id(v["vid"], c): c for v in cache.values() if v.get("result") for c in result_clips(v["result"])}
    n = 0
    for f in (WORK / "subjects").glob("*.out.json"):
        for cid, g in json.loads(f.read_text())["groups"].items():
            if cid in by_id:
                by_id[cid]["subject_group"] = g.strip().lower()
                n += 1
    save_cache(cache)
    print(f"applied {n} subject groups")


# ---------------------------------------------------------------- 3d. select + build feed data
def cmd_select(args):
    cache = load_cache()
    state = jload(STATE, {})
    clips, topics_out = [], []
    for t in enabled_topics():
        tid = t["id"]
        st = state.setdefault(tid, {"phase": "preview"})
        trusted = {c.lower() for c in t["trusted_channels"]}
        pool = []
        for v in cache.values():
            r = v.get("result")
            if not r or r.get("topic", tid) != tid or v.get("label", {}).get("topic") != tid:
                continue
            if t["require_seen_content"] and v.get("source") not in ("transcript", "chapters"):
                continue  # Sonnet never saw what is said in this clip (heatmap only)
            boost = 1 if ((t["hn_boost"] and v.get("hn")) or v["channel"].lower() in trusted) else 0
            for c in result_clips(r)[:max_clips(v, t)]:
                adj = min(10, int(c["substance"]) + boost)
                bar = t["min_substance"] if v.get("source") == "transcript" else t["min_substance_no_transcript"]
                if adj >= bar:
                    pool.append((adj, v["rank"], v, c, boost))
        pool.sort(key=lambda x: (-x[0], -x[1], x[3]["start_sec"]))
        per_chan, per_subj, chosen = {}, {}, []   # per_chan: channel -> set of its videos used
        limit = 10 if st["phase"] == "preview" else t["clips_per_topic"]
        for adj, _, v, r, boost in pool:
            vids = per_chan.setdefault(v["channel_id"], set())
            if v["vid"] not in vids and len(vids) >= t["max_videos_per_channel"]:
                continue
            subj = (r.get("subject_group") or r.get("subject") or v["vid"]).strip().lower()
            if per_subj.get(subj, 0) >= t["max_clips_per_subject"]:
                continue
            per_subj[subj] = per_subj.get(subj, 0) + 1
            vids.add(v["vid"])
            chosen.append({"id": f"{v['vid']}-{r['start_sec']}", "vid": v["vid"], "topic": tid,
                           "start": int(r["start_sec"]), "end": int(r["end_sec"]), "hook": r["hook"],
                           "why": r["why"], "substance": adj, "boosted": bool(boost), "title": v["title"],
                           "channel": v["channel"], "published": v["published"][:10], "views": v["views"],
                           "minutes": v["minutes"], "hn": bool(v.get("hn")), "source": v.get("source"),
                           "subject": subj})
            if len(chosen) >= limit:
                break
        st["clips"] = len(chosen)
        clips += chosen
        topics_out.append({"id": tid, "name": t["name"], "clips": len(chosen)})
        print(f"{tid}: {len(pool)} clips over the bar ({t['min_substance']} with transcript, "
              f"{t['min_substance_no_transcript']} without), published {len(chosen)} "
              f"(phase={st['phase']}, limit={limit})")
    jsave(STATE, state)
    (ROOT / "clips.json").write_text(json.dumps(clips, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "topics.json").write_text(json.dumps(topics_out, indent=1, ensure_ascii=False) + "\n")


def cmd_promote(args):
    state = jload(STATE, {})
    state.setdefault(args.topic, {})["phase"] = "full"
    jsave(STATE, state)
    print(f"{args.topic}: preview approved, now targets clips_per_topic")


def cmd_status(args):
    cache = load_cache()
    state = jload(STATE, {})
    for t in enabled_topics():
        mine = [v for v in cache.values() if t["id"] in v.get("found_for", [])]
        lab = [v for v in cache.values() if v.get("label", {}).get("topic") == t["id"]]
        top = top_candidates(cache, t)
        srcs = {}
        for v in top:
            srcs[v.get("source")] = srcs.get(v.get("source"), 0) + 1
        print(f"{t['id']}: found {len(mine)}, candidates {sum(v['status'] == 'candidate' for v in mine)}, "
              f"labeled {len(lab)}, top {len(top)} (sources {srcs}), scored {sum('result' in v for v in top)}, "
              f"phase {state.get(t['id'], {}).get('phase', 'new')}, published {state.get(t['id'], {}).get('clips', 0)}")
    print("API units by day:", jload(DATA / "usage.json", {}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in [("status", cmd_status), ("queries", cmd_queries), ("find", cmd_find),
                     ("label-prep", cmd_label_prep), ("label-apply", cmd_label_apply),
                     ("transcripts", cmd_transcripts), ("heatmap", cmd_heatmap), ("score-prep", cmd_score_prep),
                     ("score-apply", cmd_score_apply), ("subjects-prep", cmd_subjects_prep),
                     ("subjects-apply", cmd_subjects_apply), ("select", cmd_select)]:
        p = sub.add_parser(name)
        p.add_argument("--topic")
        p.add_argument("--limit", type=int, default=0)
        p.add_argument("--retry", action="store_true", help="transcripts: retry videos that fell back")
        p.add_argument("--rescore", action="store_true", help="score-prep: include already-scored videos")
        p.set_defaults(fn=fn)
    for name, fn in [("approve-queries", cmd_approve), ("promote", cmd_promote)]:
        p = sub.add_parser(name)
        p.add_argument("topic")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
