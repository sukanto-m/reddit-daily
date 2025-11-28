#!/usr/bin/env python3
"""
Master script to:
1) Fetch daily top posts from configured subreddits.
2) Generate a Markdown daily digest into a GitHub Pages-friendly folder.
3) On selected weekdays (e.g. Tue & Fri), also generate Twitter + LinkedIn copy.
4) On Sundays, generate a weekly 'supercut' recap + social copy.

Posting to Twitter/LinkedIn is manual: copy-paste the generated text files.
GitHub Pages will serve the Markdown from PAGES_CONTENT_DIR (e.g. /docs).
"""

import os
import datetime
import textwrap
import requests
from statistics import mean

# ========= CORE CONFIG =========

SUBREDDITS = [
    "MachineLearning",
    "dataisbeautiful",
    "LocalLLaMA",
]

# Daily config
MIN_SCORE = 100               # minimum score to include in daily + weekly digests
POSTS_PER_SUB = 15            # how many daily posts to fetch per subreddit

# Weekly config
WEEKLY_POSTS_PER_SUB = 50     # how many weekly posts to fetch per subreddit
LONG_READ_MIN_COMMENTS = 50   # threshold for "long reads" selection

# GitHub Pages config
# If your repo is configured with:
#   Settings → Pages → Build from: "Deploy from a branch", Branch: main, Folder: /docs
# then keep PAGES_CONTENT_DIR = "docs".
# If you serve directly from root, set PAGES_CONTENT_DIR = "."
PAGES_CONTENT_DIR = "docs"   # "docs" or "."

# Where Markdown digests live inside Pages content dir
DAILY_SUBDIR = "daily"
WEEKLY_SUBDIR = "weekly"

# Optional: public base URL of your GitHub Pages site.
# Example: "https://yourname.github.io/reddit-daily"
# Leave as "" if you don't want to embed links in social copy yet.
SITE_BASE_URL = ""

# Local-only dir for social copy (not served by Pages)
SOCIAL_DIR = "social"

# Weekdays (0=Monday ... 6=Sunday) to generate *daily* social copy
# Example: Tuesday (1) and Friday (4)
SOCIAL_POST_DAYS = {1, 4}

USER_AGENT = "RedditDailyDigest/0.3 by your_handle"


# ========= PATH HELPERS =========

DAILY_DIGEST_DIR = os.path.join(PAGES_CONTENT_DIR, DAILY_SUBDIR)
WEEKLY_DIGEST_DIR = os.path.join(PAGES_CONTENT_DIR, WEEKLY_SUBDIR)


def build_daily_url(date_str: str) -> str | None:
    """
    Build a public URL for the daily digest (if SITE_BASE_URL is set).
    GitHub Pages will serve the .md as HTML, typically at /daily/<file>.html
    """
    if not SITE_BASE_URL:
        return None
    base = SITE_BASE_URL.rstrip("/")
    return f"{base}/{DAILY_SUBDIR}/reddit_daily_{date_str}.html"


def build_weekly_url(date_str: str, week_label: str) -> str | None:
    """
    Build a public URL for the weekly digest (if SITE_BASE_URL is set).
    """
    if not SITE_BASE_URL:
        return None
    base = SITE_BASE_URL.rstrip("/")
    return f"{base}/{WEEKLY_SUBDIR}/reddit_weekly_{date_str}.html"


# ========= HTTP / REDDIT HELPERS =========

def fetch_daily_top(subreddit, limit=POSTS_PER_SUB, min_score=MIN_SCORE):
    """
    Fetch top posts for the last 24 hours from a subreddit.
    Returns a list of dicts with keys: title, url, score, sub, num_comments, is_self.
    """
    url = f"https://www.reddit.com/r/{subreddit}/top.json"
    params = {"t": "day", "limit": limit}
    headers = {"User-Agent": USER_AGENT}

    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    raw_posts = resp.json().get("data", {}).get("children", [])

    posts = []
    for p in raw_posts:
        d = p.get("data", {})
        score = d.get("score", 0)
        if score < min_score:
            continue

        posts.append(
            {
                "sub": subreddit,
                "title": d.get("title", "").strip(),
                "url": "https://reddit.com" + d.get("permalink", ""),
                "score": score,
                "num_comments": d.get("num_comments", 0),
                "is_self": d.get("is_self", False),
            }
        )

    return posts


def fetch_weekly_top(subreddit, limit=WEEKLY_POSTS_PER_SUB, min_score=MIN_SCORE):
    """
    Fetch top posts for the last week from a subreddit.
    Used for the Sunday weekly supercut.
    """
    url = f"https://www.reddit.com/r/{subreddit}/top.json"
    params = {"t": "week", "limit": limit}
    headers = {"User-Agent": USER_AGENT}

    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    raw_posts = resp.json().get("data", {}).get("children", [])

    posts = []
    for p in raw_posts:
        d = p.get("data", {})
        score = d.get("score", 0)
        if score < min_score:
            continue

        posts.append(
            {
                "sub": subreddit,
                "title": d.get("title", "").strip(),
                "url": "https://reddit.com" + d.get("permalink", ""),
                "score": score,
                "num_comments": d.get("num_comments", 0),
                "is_self": d.get("is_self", False),
            }
        )

    return posts


# ========= SHARED HELPERS =========

def build_one_line_vibe(posts):
    """
    Very simple heuristic 'vibe' line based on average score.
    You can swap this for something smarter later.
    """
    if not posts:
        return "Quiet feed. Fewer posts, more breathing room."

    total = len(posts)
    avg_score = sum(p["score"] for p in posts) / total

    if avg_score > 800:
        return "High-signal chaos: big scores, busy threads, almost no cheap takes."
    elif avg_score > 400:
        return "Solid mix of practical tips, charts, and mild hardware coping."
    else:
        return "Slow burn: niche threads, thoughtful comments, fewer fireworks."


def truncate_tweet(text, limit=280):
    """
    Ensure a tweet stays within the character limit.
    """
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


# ========= DAILY DIGEST BUILDERS =========

def build_daily_digest_markdown(date_str, posts_by_sub, generated_time_str):
    """
    Build the full Markdown daily digest string.
    posts_by_sub: dict[subreddit] = list[post]
    """
    all_posts = [p for posts in posts_by_sub.values() for p in posts]
    all_posts_sorted = sorted(all_posts, key=lambda p: p["score"], reverse=True)

    subreddit_list = ", ".join(f"r/{s}" for s in SUBREDDITS)
    total_scanned = len(all_posts)
    kept_posts = total_scanned  # already filtered by MIN_SCORE

    one_line_vibe = build_one_line_vibe(all_posts)
    filters_applied = (
        f"Top posts by score (t=day), min score {MIN_SCORE}, NSFW implicitly filtered by your Reddit prefs"
    )

    # Front page: top 3 across all subs
    top3 = all_posts_sorted[:3]
    top_stories_lines = []
    for i, p in enumerate(top3, start=1):
        line_title = f"{i}. (**r/{p['sub']}**, {p['score']}★) [{p['title']}]({p['url']})"
        top_stories_lines.append(line_title)
    top_stories_block = "\n".join(top_stories_lines) if top_stories_lines else "_No standout posts today._"

    # By subreddit
    per_sub_blocks = []
    for sub in SUBREDDITS:
        posts = posts_by_sub.get(sub, [])
        if not posts:
            continue

        heading = f"### r/{sub}\n"
        sub_summary = "_Today’s highlights from this corner of Reddit._\n"
        post_lines = [
            f"- ({p['score']}★) [{p['title']}]({p['url']})"
            for p in posts
        ]
        block = "\n".join([heading, sub_summary] + post_lines + [""])
        per_sub_blocks.append(block)

    per_subreddit_blocks = "\n".join(per_sub_blocks) if per_sub_blocks else "_No qualifying posts today._"

    # Long reads: high comment threads
    long_candidates = [p for p in all_posts_sorted if p["num_comments"] >= LONG_READ_MIN_COMMENTS]
    long_reads = long_candidates[:5]
    if long_reads:
        long_lines = [
            f"- (**r/{p['sub']}**, {p['score']}★, {p['num_comments']}💬) [{p['title']}]({p['url']})"
            for p in long_reads
        ]
        long_reads_block = "\n".join(long_lines)
    else:
        long_reads_block = "Nothing particularly long today – everyone’s shitposting."

    # Patterns (placeholder)
    patterns_block = (
        "- Practical threads dominated most subs.\n"
        "- Charts and visualisations stayed strong in r/dataisbeautiful.\n"
        "- Local LLMs continue to be a magnet for hardware pain and clever hacks."
    )

    md = f"""# Reddit Daily – {date_str}

Curated from: {subreddit_list}

---

## Snapshot

- Total posts scanned: **{total_scanned}**
- Posts in this digest: **{kept_posts}**
- Time window: **Last 24 hours**
- Filters: {filters_applied}

**Today’s vibe:** {one_line_vibe}

---

## Front Page – Top Stories

{top_stories_block}

---

## By Subreddit

{per_subreddit_blocks}

---

## Long Reads / Deep Dives

{long_reads_block}

---

## Patterns & Curiosities

{patterns_block}

---

_Compiled automatically at {generated_time_str}. Links may age, curiosity doesn’t._
"""
    return md.strip() + "\n"


def build_daily_twitter_thread(date_str, one_line_vibe, all_posts_sorted, posts_by_sub, digest_url=None):
    """
    Return a list of tweet texts (in order) for the daily short thread.
    """
    # Tweet 1: hook
    t1 = f"Reddit Daily – {date_str}\nToday’s vibe: {one_line_vibe}"

    # Tweet 2: top stories
    top3 = all_posts_sorted[:3]
    lines = ["Top stories:"]
    for p in top3:
        line = f"• r/{p['sub']} – {p['title'][:80]}"
        lines.append(line)
    t2 = "\n".join(lines) if len(lines) > 1 else "Top stories: quiet day on the front page."

    # Tweet 3: per-subreddit compact summary
    sub_lines = ["By subreddit:"]
    for sub in SUBREDDITS:
        posts = posts_by_sub.get(sub, [])
        if not posts:
            continue
        top_title = posts[0]["title"][:70] if posts else "No notable posts."
        sub_lines.append(f"• r/{sub} – {top_title}")
    t3 = "\n".join(sub_lines)

    tweets = [truncate_tweet(t) for t in (t1, t2, t3) if t.strip()]
    if digest_url:
        tweets.append(truncate_tweet(f"Full digest + links: {digest_url}"))

    return tweets


def build_daily_linkedin_post(date_str, one_line_vibe, posts_by_sub, digest_url=None):
    """
    Build a longer-form LinkedIn post text for the daily recap.
    """
    intro = f"🚀 Reddit Daily – {date_str}\n\nIf you missed Reddit today, here’s what actually mattered 👇"
    theme = f"💡 Theme\n{one_line_vibe}\n"

    # Signals per subreddit
    signals_lines = ["🔥 Signals from the trenches"]
    for sub in SUBREDDITS:
        posts = posts_by_sub.get(sub, [])
        if not posts:
            continue
        top_post = posts[0]
        signals_lines.append(f"• r/{sub} → {top_post['title']}")
    signals = "\n".join(signals_lines)

    why = textwrap.dedent(
        """\
        📊 Why this matters
        Practitioners are quietly reshaping how AI gets built and deployed:
        • More focus on efficiency and local tooling
        • Visual storytelling through data (maps, charts, animations)
        • Real-world constraints driving design decisions, not just benchmarks
        """
    )

    url_block = f"\n🔗 Full digest\n{digest_url}" if digest_url else ""

    outro = textwrap.dedent(
        """\
        🧭 My read
        The interesting work is happening in the margins — small models, scrappy setups, careful visualisation.
        That’s where the next wave of practical AI impact is coming from.

        #MachineLearning #Data #AI #RedditResearch
        """
    )

    parts = [intro, theme, signals, "", why, url_block, "", outro]
    post = "\n".join(p for p in parts if p is not None)
    return post.strip() + "\n"


# ========= WEEKLY SUPER-CUT BUILDERS =========

def build_weekly_supercut_markdown(week_label, posts_by_sub, generated_time_str):
    """
    Build a weekly 'supercut' Markdown report for the entire week.
    week_label: string like 'Week of 2025-11-24 to 2025-11-30'
    posts_by_sub: dict[subreddit] = list[post] for the week.
    """
    all_posts = [p for posts in posts_by_sub.values() for p in posts]
    all_sorted = sorted(all_posts, key=lambda p: p["score"], reverse=True)

    subreddit_list = ", ".join(f"r/{s}" for s in SUBREDDITS)
    total_scanned = len(all_posts)

    one_line_vibe = build_one_line_vibe(all_posts)

    # Weekly front page: top 7
    top_n = all_sorted[:7]
    if top_n:
        front_lines = []
        for i, p in enumerate(top_n, start=1):
            front_lines.append(
                f"{i}. (**r/{p['sub']}**, {p['score']}★, {p['num_comments']}💬) "
                f"[{p['title']}]({p['url']})"
            )
        weekly_front_block = "\n".join(front_lines)
    else:
        weekly_front_block = "_Not much action this week._"

    # Per subreddit weekly stats
    per_sub_blocks = []
    for sub in SUBREDDITS:
        posts = posts_by_sub.get(sub, [])
        if not posts:
            continue

        scores = [p["score"] for p in posts]
        avg_score = mean(scores) if scores else 0
        top_post = max(posts, key=lambda p: p["score"])

        heading = f"### r/{sub}\n"
        summary_lines = [
            f"- Posts in recap: **{len(posts)}**",
            f"- Average score: **{int(avg_score)}★**",
            f"- Top post: [{top_post['title']}]({top_post['url']})  ({top_post['score']}★, {top_post['num_comments']}💬)",
        ]
        block = "\n".join([heading] + summary_lines + [""])
        per_sub_blocks.append(block)

    per_subreddit_blocks = "\n".join(per_sub_blocks) if per_sub_blocks else "_No qualifying posts this week._"

    # Long reads / rabbit holes (weekly)
    long_candidates = [p for p in all_sorted if p["num_comments"] >= LONG_READ_MIN_COMMENTS]
    long_reads = long_candidates[:10]
    if long_reads:
        lr_lines = [
            f"- (**r/{p['sub']}**, {p['score']}★, {p['num_comments']}💬) [{p['title']}]({p['url']})"
            for p in long_reads
        ]
        long_reads_block = "\n".join(lr_lines)
    else:
        long_reads_block = "Quiet week for essays – more quick hits than deep dives."

    # Patterns & shifts (basic for now)
    patterns_lines = [
        f"- Overall vibe: {one_line_vibe}",
        "- r/MachineLearning and r/LocalLLaMA leaned into small, efficient models.",
        "- r/dataisbeautiful stayed strong on long-term time series and climate / geography visuals.",
        "- Hardware pain, quantisation experiments, and messy reality show up consistently in comments.",
    ]
    patterns_block = "\n".join(patterns_lines)

    md = f"""# Reddit Weekly – {week_label}

Curated from: {subreddit_list}

---

## Weekly Snapshot

- Total posts considered: **{total_scanned}**
- Time window: **{week_label}**
- Filters: Top posts (t=week), min score {MIN_SCORE}, NSFW implicitly filtered by your Reddit prefs

**Weekly vibe:** {one_line_vibe}

---

## Weekly Front Page – Top Posts

{weekly_front_block}

---

## By Subreddit – Weekly Highlights

{per_subreddit_blocks}

---

## Long Reads & Rabbit Holes

{long_reads_block}

---

## Patterns & Shifts

{patterns_block}

---

_Compiled automatically at {generated_time_str}. Good weeks blur, well-curated links don’t._
"""
    return md.strip() + "\n"


def build_weekly_twitter_thread(week_label, all_posts_sorted, posts_by_sub, digest_url=None):
    """
    Build a short Twitter thread for the weekly supercut.
    """
    # Tweet 1 – headline
    t1 = f"Reddit AI Weekly – {week_label}\nWhat actually stood out this week 👇"

    # Tweet 2 – top posts
    top5 = all_posts_sorted[:5]
    lines = ["Top posts of the week:"]
    for p in top5:
        lines.append(f"• r/{p['sub']} – {p['title'][:80]}")
    t2 = "\n".join(lines) if len(lines) > 1 else "Top posts: surprisingly quiet week."

    # Tweet 3 – most active subs
    sub_activity = [
        (sub, len(posts_by_sub.get(sub, [])))
        for sub in SUBREDDITS
    ]
    sub_activity = [x for x in sub_activity if x[1] > 0]
    sub_activity.sort(key=lambda x: x[1], reverse=True)

    lines3 = ["Most active subs:"]
    for sub, count in sub_activity:
        lines3.append(f"• r/{sub} – {count} posts in recap")
    t3 = "\n".join(lines3) if len(lines3) > 1 else "Most active subs: nothing major this week."

    tweets = [truncate_tweet(t) for t in (t1, t2, t3) if t.strip()]
    if digest_url:
        tweets.append(truncate_tweet(f"Full weekly recap + links: {digest_url}"))

    return tweets


def build_weekly_linkedin_post(week_label, posts_by_sub, digest_url=None):
    """
    Build a LinkedIn-style weekly recap post.
    """
    intro = f"📅 Reddit Weekly – {week_label}\n\nZooming out on a week of AI / data conversations across a few signal-heavy subreddits 👇"

    # Simple signals
    signals_lines = ["🔥 Weekly signals from the trenches"]
    for sub in SUBREDDITS:
        posts = posts_by_sub.get(sub, [])
        if not posts:
            continue
        top_post = max(posts, key=lambda p: p["score"])
        signals_lines.append(f"• r/{sub} → {top_post['title']} ({top_post['score']}★, {top_post['num_comments']}💬)")
    signals = "\n".join(signals_lines)

    why = textwrap.dedent(
        """\
        📊 Why this matters
        Looking at a full week smooths out hype spikes and exposes the slow, structural shifts:
        • Which topics practitioners keep coming back to
        • Where the most engaged discussions are (comments, not just upvotes)
        • How tooling, deployment patterns, and visualisation practices are evolving
        """
    )

    url_block = f"\n🔗 Full weekly digest\n{digest_url}" if digest_url else ""

    outro = textwrap.dedent(
        """\
        🧭 My read
        The real story isn’t in single viral posts, but in the quiet repetition of themes across days:
        small, efficient models; scrappy local setups; and people trying to make sense of complex data in public.

        #MachineLearning #AI #Data #RedditResearch #WeeklyRecap
        """
    )

    parts = [intro, "", signals, "", why, url_block, "", outro]
    post = "\n".join(p for p in parts if p is not None)
    return post.strip() + "\n"


# ========= INDEX GENERATOR (optional but nice) =========

def update_site_index():
    """
    Generate/overwrite an index.md at PAGES_CONTENT_DIR listing daily + weekly digests.
    This is optional but makes GitHub Pages nicer to browse.
    """
    os.makedirs(PAGES_CONTENT_DIR, exist_ok=True)

    daily_entries = []
    if os.path.isdir(DAILY_DIGEST_DIR):
        for fname in os.listdir(DAILY_DIGEST_DIR):
            if fname.startswith("reddit_daily_") and fname.endswith(".md"):
                date_part = fname[len("reddit_daily_"):-3]
                daily_entries.append((date_part, fname))
        daily_entries.sort(reverse=True)

    weekly_entries = []
    if os.path.isdir(WEEKLY_DIGEST_DIR):
        for fname in os.listdir(WEEKLY_DIGEST_DIR):
            if fname.startswith("reddit_weekly_") and fname.endswith(".md"):
                date_part = fname[len("reddit_weekly_"):-3]
                weekly_entries.append((date_part, fname))
        weekly_entries.sort(reverse=True)

    lines = [
        "# Reddit Briefs",
        "",
        "Auto-generated index of daily and weekly Reddit digests.",
        "",
    ]

    if daily_entries:
        lines.append("## Daily digests")
        lines.append("")
        for date_part, fname in daily_entries:
            # Use extension-less link so GitHub Pages serves HTML
            url = f"{DAILY_SUBDIR}/reddit_daily_{date_part}"
            lines.append(f"- **{date_part}** – [Daily digest]({url})")
        lines.append("")

    if weekly_entries:
        lines.append("## Weekly supercuts")
        lines.append("")
        for date_part, fname in weekly_entries:
            url = f"{WEEKLY_SUBDIR}/reddit_weekly_{date_part}"
            lines.append(f"- **{date_part}** – [Weekly recap]({url})")
        lines.append("")

    index_path = os.path.join(PAGES_CONTENT_DIR, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[OK] Site index updated at: {index_path}")


# ========= MAIN ORCHESTRATOR =========

def ensure_dirs():
    os.makedirs(DAILY_DIGEST_DIR, exist_ok=True)
    os.makedirs(WEEKLY_DIGEST_DIR, exist_ok=True)
    os.makedirs(SOCIAL_DIR, exist_ok=True)


def main():
    ensure_dirs()

    today = datetime.date.today()
    now = datetime.datetime.now()
    date_str = today.isoformat()
    generated_time_str = now.strftime("%Y-%m-%d %H:%M")

    print(f"[INFO] Building Reddit Daily for {date_str}")

    # ---- 1. Daily fetch ----
    posts_by_sub_daily = {}
    for sub in SUBREDDITS:
        try:
            posts = fetch_daily_top(sub)
            posts_by_sub_daily[sub] = sorted(posts, key=lambda p: p["score"], reverse=True)
            print(f"[INFO] Daily – r/{sub}: {len(posts)} posts kept")
        except Exception as e:
            print(f"[WARN] Daily fetch failed for r/{sub}: {e}")
            posts_by_sub_daily[sub] = []

    all_daily_posts = [p for posts in posts_by_sub_daily.values() for p in posts]
    all_daily_sorted = sorted(all_daily_posts, key=lambda p: p["score"], reverse=True)

    # ---- 2. Daily digest markdown ----
    daily_md = build_daily_digest_markdown(date_str, posts_by_sub_daily, generated_time_str)
    daily_filename = f"reddit_daily_{date_str}.md"
    daily_path = os.path.join(DAILY_DIGEST_DIR, daily_filename)
    with open(daily_path, "w", encoding="utf-8") as f:
        f.write(daily_md)
    print(f"[OK] Daily digest written to: {daily_path}")

    # ---- 3. Daily social (Tue & Fri by default) ----
    weekday = today.weekday()  # 0=Mon ... 6=Sun
    if weekday in SOCIAL_POST_DAYS and all_daily_posts:
        print("[INFO] Social post day – generating DAILY Twitter + LinkedIn copy")
        daily_vibe = build_one_line_vibe(all_daily_posts)
        digest_url = build_daily_url(date_str)

        # Twitter thread (daily)
        tweets_daily = build_daily_twitter_thread(date_str, daily_vibe, all_daily_sorted, posts_by_sub_daily, digest_url)
        twitter_daily_path = os.path.join(SOCIAL_DIR, f"twitter_thread_{date_str}.txt")
        with open(twitter_daily_path, "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(tweets_daily))
        print(f"[OK] Daily Twitter thread written to: {twitter_daily_path}")

        # LinkedIn post (daily)
        linkedin_daily = build_daily_linkedin_post(date_str, daily_vibe, posts_by_sub_daily, digest_url)
        linkedin_daily_path = os.path.join(SOCIAL_DIR, f"linkedin_post_{date_str}.txt")
        with open(linkedin_daily_path, "w", encoding="utf-8") as f:
            f.write(linkedin_daily)
        print(f"[OK] Daily LinkedIn post written to: {linkedin_daily_path}")
    else:
        print("[INFO] Not a daily social post day. Skipping DAILY Twitter/LinkedIn generation.")

    # ---- 4. Weekly supercut (Sunday only) ----
    if weekday == 6:  # Sunday
        print("[INFO] Sunday – building WEEKLY supercut")
        posts_by_sub_weekly = {}
        for sub in SUBREDDITS:
            try:
                w_posts = fetch_weekly_top(sub)
                posts_by_sub_weekly[sub] = sorted(w_posts, key=lambda p: p["score"], reverse=True)
                print(f"[INFO] Weekly – r/{sub}: {len(w_posts)} posts kept")
            except Exception as e:
                print(f"[WARN] Weekly fetch failed for r/{sub}: {e}")
                posts_by_sub_weekly[sub] = []

        all_weekly_posts = [p for posts in posts_by_sub_weekly.values() for p in posts]
        all_weekly_sorted = sorted(all_weekly_posts, key=lambda p: p["score"], reverse=True)

        # Define week label (Mon–Sun window ending today)
        start_of_week = today - datetime.timedelta(days=6)
        week_label = f"Week of {start_of_week.isoformat()} to {today.isoformat()}"

        weekly_md = build_weekly_supercut_markdown(week_label, posts_by_sub_weekly, generated_time_str)
        weekly_filename = f"reddit_weekly_{date_str}.md"
        weekly_path = os.path.join(WEEKLY_DIGEST_DIR, weekly_filename)
        with open(weekly_path, "w", encoding="utf-8") as f:
            f.write(weekly_md)
        print(f"[OK] Weekly supercut written to: {weekly_path}")

        if all_weekly_posts:
            print("[INFO] Generating WEEKLY Twitter + LinkedIn copy")
            digest_url_weekly = build_weekly_url(date_str, week_label)

            # Weekly Twitter thread
            tweets_weekly = build_weekly_twitter_thread(week_label, all_weekly_sorted, posts_by_sub_weekly, digest_url_weekly)
            twitter_weekly_path = os.path.join(SOCIAL_DIR, f"twitter_weekly_{date_str}.txt")
            with open(twitter_weekly_path, "w", encoding="utf-8") as f:
                f.write("\n\n---\n\n".join(tweets_weekly))
            print(f"[OK] Weekly Twitter thread written to: {twitter_weekly_path}")

            # Weekly LinkedIn post
            linkedin_weekly = build_weekly_linkedin_post(week_label, posts_by_sub_weekly, digest_url_weekly)
            linkedin_weekly_path = os.path.join(SOCIAL_DIR, f"linkedin_weekly_{date_str}.txt")
            with open(linkedin_weekly_path, "w", encoding="utf-8") as f:
                f.write(linkedin_weekly)
            print(f"[OK] Weekly LinkedIn post written to: {linkedin_weekly_path}")
        else:
            print("[INFO] No weekly posts to summarise; skipping weekly social copy.")
    else:
        print("[INFO] Not Sunday – skipping weekly supercut.")

    # ---- 5. Update GitHub Pages index ----
    update_site_index()


if __name__ == "__main__":
    main()
