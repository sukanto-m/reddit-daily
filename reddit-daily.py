#!/usr/bin/env python3
"""
Master script to:
1) Fetch daily top posts from configured subreddits.
2) Generate a Markdown daily digest into a GitHub Pages-friendly folder.
3) On selected weekdays (e.g. Tue & Fri), also generate Twitter + LinkedIn copy.
4) On Sundays, generate a weekly 'supercut' recap + social copy.
5) Maintain an RSS feed (rss.xml) for daily digests.

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
MIN_SCORE = 100
POSTS_PER_SUB = 15

# Weekly config
WEEKLY_POSTS_PER_SUB = 50
LONG_READ_MIN_COMMENTS = 50

# GitHub Pages config
PAGES_CONTENT_DIR = "docs"
DAILY_SUBDIR = "daily"
WEEKLY_SUBDIR = "weekly"

# Optional: set your public site URL so social copy includes clickable links
# Example: "https://username.github.io/Reddit-Daily"
SITE_BASE_URL = ""

# Local folder for Twitter/LinkedIn/Caption drafts
SOCIAL_DIR = "social"

# Tue=1, Fri=4
SOCIAL_POST_DAYS = {1, 4}

USER_AGENT = "RedditDailyDigest/0.4 by your_handle"

# ========= PATH HELPERS =========

DAILY_DIGEST_DIR = os.path.join(PAGES_CONTENT_DIR, DAILY_SUBDIR)
WEEKLY_DIGEST_DIR = os.path.join(PAGES_CONTENT_DIR, WEEKLY_SUBDIR)


def build_daily_url(date_str: str) -> str | None:
    if not SITE_BASE_URL:
        return None
    base = SITE_BASE_URL.rstrip("/")
    return f"{base}/{DAILY_SUBDIR}/reddit_daily_{date_str}.html"


def build_weekly_url(date_str: str, week_label: str) -> str | None:
    if not SITE_BASE_URL:
        return None
    base = SITE_BASE_URL.rstrip("/")
    return f"{base}/{WEEKLY_SUBDIR}/reddit_weekly_{date_str}.html"


# ========= HTTP / REDDIT HELPERS =========

def fetch_daily_top(subreddit, limit=POSTS_PER_SUB, min_score=MIN_SCORE):
    url = f"https://www.reddit.com/r/{subreddit}/top.json"
    params = {"t": "day", "limit": limit}
    headers = {"User-Agent": USER_AGENT}

    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    raw_posts = resp.json().get("data", {}).get("children", [])

    posts = []
    for p in raw_posts:
        d = p.get("data", {})
        if d.get("score", 0) < min_score:
            continue
        posts.append({
            "sub": subreddit,
            "title": d.get("title", "").strip(),
            "url": "https://reddit.com" + d.get("permalink", ""),
            "score": d.get("score", 0),
            "num_comments": d.get("num_comments", 0),
            "is_self": d.get("is_self", False),
        })
    return posts


def fetch_weekly_top(subreddit, limit=WEEKLY_POSTS_PER_SUB, min_score=MIN_SCORE):
    url = f"https://www.reddit.com/r/{subreddit}/top.json"
    params = {"t": "week", "limit": limit}
    headers = {"User-Agent": USER_AGENT}

    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    raw_posts = resp.json().get("data", {}).get("children", [])

    posts = []
    for p in raw_posts:
        d = p.get("data", {})
        if d.get("score", 0) < min_score:
            continue
        posts.append({
            "sub": subreddit,
            "title": d.get("title", "").strip(),
            "url": "https://reddit.com" + d.get("permalink", ""),
            "score": d.get("score", 0),
            "num_comments": d.get("num_comments", 0),
            "is_self": d.get("is_self", False),
        })
    return posts


# ========= SHARED HELPERS =========

def build_one_line_vibe(posts):
    if not posts:
        return "Quiet feed. Fewer posts, more breathing room."

    avg = sum(p["score"] for p in posts) / len(posts)
    if avg > 800:
        return "High-signal chaos: big scores, busy threads, almost no cheap takes."
    elif avg > 400:
        return "Solid mix of practical tips, charts, and mild hardware coping."
    else:
        return "Slow burn: niche threads, thoughtful comments, fewer fireworks."


def truncate_tweet(text, limit=280):
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


# ========= DAILY DIGEST BUILDERS =========

def build_daily_digest_markdown(date_str, posts_by_sub, generated_time_str):
    all_posts = [p for posts in posts_by_sub.values() for p in posts]
    all_sorted = sorted(all_posts, key=lambda p: p["score"], reverse=True)

    subreddit_list = ", ".join(f"r/{s}" for s in SUBREDDITS)
    vibe = build_one_line_vibe(all_posts)

    top3 = all_sorted[:3]
    top_lines = [
        f"{i+1}. (**r/{p['sub']}**, {p['score']}★) [{p['title']}]({p['url']})"
        for i, p in enumerate(top3)
    ] if top3 else ["_Nothing stood out today_"]

    per_sub_blocks = []
    for sub, posts in posts_by_sub.items():
        if not posts:
            continue
        block = "### r/" + sub + "\n" + "\n".join(
            f"- ({p['score']}★) [{p['title']}]({p['url']})"
            for p in posts
        )
        per_sub_blocks.append(block + "\n")

    long_reads = [
        p for p in all_sorted if p["num_comments"] >= LONG_READ_MIN_COMMENTS
    ][:5]
    long_block = "\n".join(
        f"- (**r/{p['sub']}**, {p['score']}★, {p['num_comments']}💬) [{p['title']}]({p['url']})"
        for p in long_reads
    ) if long_reads else "Nothing particularly long today – everyone’s shitposting."

    md = f"""# Reddit Daily – {date_str}

Curated from: {subreddit_list}

**Today’s vibe:** {vibe}

## Front Page – Top Stories
{chr(10).join(top_lines)}

## By Subreddit
{chr(10).join(per_sub_blocks) if per_sub_blocks else "_No qualifying posts_"}

## Long Reads
{long_block}

_Compiled automatically at {generated_time_str}_
"""
    return md.strip() + "\n"


def build_daily_twitter_thread(date_str, vibe, all_sorted, posts_by_sub, digest_url=None):
    top3 = all_sorted[:3]
    t1 = f"Reddit Daily – {date_str}\nToday’s vibe: {vibe}"
    t2 = "Top stories:\n" + "\n".join(
        f"• r/{p['sub']} – {p['title'][:80]}" for p in top3
    ) if top3 else "Quiet front page."
    t3 = "By subreddit:\n" + "\n".join(
        f"• r/{s} – {posts_by_sub[s][0]['title'][:70]}" for s in SUBREDDITS if posts_by_sub[s]
    )
    tweets = [truncate_tweet(t) for t in (t1, t2, t3)]
    if digest_url:
        tweets.append(truncate_tweet(f"Full digest: {digest_url}"))
    return tweets


def build_daily_linkedin_post(date_str, vibe, posts_by_sub, digest_url=None):
    intro = f"🚀 Reddit Daily – {date_str}\n\nMissed Reddit today? Here’s what mattered 👇"
    theme = f"💡 Theme\n{vibe}\n"
    signals = "🔥 Signals\n" + "\n".join(
        f"• r/{s} → {posts_by_sub[s][0]['title']}" for s in SUBREDDITS if posts_by_sub[s]
    )
    why = "📊 Why this matters\nPeople are shipping ideas in public, not polishing decks."
    url = f"\n🔗 Full digest\n{digest_url}" if digest_url else ""
    outro = "#MachineLearning #AI #RedditResearch"
    return "\n".join([intro, theme, signals, "", why, url, "", outro]).strip() + "\n"


# ========= WEEKLY SUPER-CUT BUILDERS =========

def build_weekly_supercut_markdown(week_label, posts_by_sub, generated_time_str):
    all_posts = [p for posts in posts_by_sub.values() for p in posts]
    all_sorted = sorted(all_posts, key=lambda p: p["score"], reverse=True)
    vibe = build_one_line_vibe(all_posts)

    top7 = all_sorted[:7]
    front = "\n".join(
        f"{i+1}. (**r/{p['sub']}**, {p['score']}★, {p['num_comments']}💬) [{p['title']}]({p['url']})"
        for i, p in enumerate(top7)
    ) if top7 else "_Quiet week_"

    per_sub = []
    for sub, posts in posts_by_sub.items():
        if not posts:
            continue
        scores = [p["score"] for p in posts]
        avg = int(sum(scores) / len(scores))
        best = max(posts, key=lambda p: p["score"])
        per_sub.append(
            f"### r/{sub}\n- Posts: **{len(posts)}**\n- Avg score: **{avg}**\n- Top: [{best['title']}]({best['url']})"
        )

    long_reads = [
        p for p in all_sorted if p["num_comments"] >= LONG_READ_MIN_COMMENTS
    ][:10]
    long = "\n".join(
        f"- (**r/{p['sub']}**, {p['score']}★, {p['num_comments']}💬) [{p['title']}]({p['url']})"
        for p in long_reads
    ) if long_reads else "_No deep dives_"

    md = f"""# Reddit Weekly – {week_label}

**Weekly vibe:** {vibe}

## Front Page – Top Posts
{front}

## By Subreddit
{chr(10).join(per_sub) if per_sub else "_Nothing major_"}

## Long Reads
{long}

_Compiled at {generated_time_str}_
"""
    return md.strip() + "\n"


def build_weekly_twitter_thread(week_label, all_sorted, posts_by_sub, digest_url=None):
    t1 = f"Reddit AI Weekly – {week_label}\nWhat stood out 👇"
    top5 = all_sorted[:5]
    t2 = "Top posts:\n" + "\n".join(
        f"• r/{p['sub']} – {p['title'][:80]}" for p in top5
    ) if top5 else "_Quiet_"
    t3 = "Most active subs:\n" + "\n".join(
        f"• r/{s} – {len(posts_by_sub[s])}" for s in SUBREDDITS if posts_by_sub[s]
    )
    tweets = [truncate_tweet(t) for t in (t1, t2, t3)]
    if digest_url:
        tweets.append(truncate_tweet(f"Full recap: {digest_url}"))
    return tweets


def build_weekly_linkedin_post(week_label, posts_by_sub, digest_url=None):
    intro = f"📅 Reddit Weekly – {week_label}\nZooming out on the week 👇"
    signals = "🔥 Signals\n" + "\n".join(
        f"• r/{s} → {max(posts_by_sub[s], key=lambda p: p['score'])['title']}"
        for s in SUBREDDITS if posts_by_sub[s]
    )
    why = "📊 Why this matters\nTrends reveal themselves in repetition, not noise."
    url = f"\n🔗 Full weekly digest\n{digest_url}" if digest_url else ""
    outro = "#MachineLearning #AI #WeeklyRecap"
    return "\n".join([intro, "", signals, "", why, url, "", outro]).strip() + "\n"


# ========= RSS GENERATOR =========

def update_rss_feed():
    """
    Generate or update rss.xml based on existing daily digests in docs/daily.
    Only includes the last ~30 digests to keep size manageable.
    """
    if not os.path.isdir(DAILY_DIGEST_DIR):
        print("[INFO] No daily digests yet; skipping RSS feed update.")
        return

    # Collect date parts from filenames
    dates = []
    for fname in os.listdir(DAILY_DIGEST_DIR):
        if fname.startswith("reddit_daily_") and fname.endswith(".md"):
            date_part = fname[len("reddit_daily_"):-3]  # strip prefix + ".md"
            dates.append(date_part)

    if not dates:
        print("[INFO] No daily digests found; skipping RSS feed update.")
        return

    dates.sort(reverse=True)
    dates = dates[:30]  # last 30 digests

    items = []
    for date_str in dates:
        url = build_daily_url(date_str)
        if not url:
            # fallback relative URL if SITE_BASE_URL not set
            if SITE_BASE_URL:
                base = SITE_BASE_URL.rstrip("/")
                url = f"{base}/{DAILY_SUBDIR}/reddit_daily_{date_str}.html"
            else:
                url = f"{DAILY_SUBDIR}/reddit_daily_{date_str}.html"

        title = f"Reddit Daily – {date_str}"
        # Try to parse date_str as YYYY-MM-DD
        try:
            d = datetime.date.fromisoformat(date_str)
            dt = datetime.datetime.combine(d, datetime.time())
        except Exception:
            dt = datetime.datetime.utcnow()

        pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        description = "Daily Reddit digest covering AI, ML, and data threads."

        items.append(f"""  <item>
    <title>{title}</title>
    <link>{url}</link>
    <guid>{url}</guid>
    <pubDate>{pub_date}</pubDate>
    <description><![CDATA[{description}]]></description>
  </item>""")

    channel_link = SITE_BASE_URL or ""
    items_xml = os.linesep.join(items)

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Reddit Daily – RSS Feed</title>
  <link>{channel_link}</link>
  <description>Automatic digest of top posts from AI / data subreddits.</description>
  <language>en-us</language>
{items_xml}
</channel>
</rss>
"""

    rss_path = os.path.join(PAGES_CONTENT_DIR, "rss.xml")
    with open(rss_path, "w", encoding="utf-8") as f:
        f.write(rss_xml)
    print(f"[OK] RSS feed updated at: {rss_path}")


# ========= INDEX GENERATOR =========

def update_site_index():
    os.makedirs(PAGES_CONTENT_DIR, exist_ok=True)

    daily_entries = []
    if os.path.isdir(DAILY_DIGEST_DIR):
        for f in os.listdir(DAILY_DIGEST_DIR):
            if f.startswith("reddit_daily_") and f.endswith(".md"):
                daily_entries.append((f[13:-3], f))
        daily_entries.sort(reverse=True)

    weekly_entries = []
    if os.path.isdir(WEEKLY_DIGEST_DIR):
        for f in os.listdir(WEEKLY_DIGEST_DIR):
            if f.startswith("reddit_weekly_") and f.endswith(".md"):
                weekly_entries.append((f[14:-3], f))
        weekly_entries.sort(reverse=True)

    lines = ["# Reddit Briefs", "", "Auto-generated index", ""]
    if daily_entries:
        lines.append("## Daily")
        lines.extend(
            f"- **{d}** – [Daily]({DAILY_SUBDIR}/reddit_daily_{d})"
            for d, _ in daily_entries
        )
        lines.append("")
    if weekly_entries:
        lines.append("## Weekly")
        lines.extend(
            f"- **{d}** – [Weekly]({WEEKLY_SUBDIR}/reddit_weekly_{d})"
            for d, _ in weekly_entries
        )
        lines.append("")

    with open(os.path.join(PAGES_CONTENT_DIR, "index.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("[OK] index updated")


# ========= MAIN =========

def ensure_dirs():
    os.makedirs(DAILY_DIGEST_DIR, exist_ok=True)
    os.makedirs(WEEKLY_DIGEST_DIR, exist_ok=True)
    os.makedirs(SOCIAL_DIR, exist_ok=True)


def main():
    ensure_dirs()
    today = datetime.date.today()
    now = datetime.datetime.now()
    date_str = today.isoformat()
    ts = now.strftime("%Y-%m-%d %H:%M")

    print(f"[INFO] Running for {date_str}")

    # DAILY FETCH
    posts_by_sub_daily = {}
    for sub in SUBREDDITS:
        try:
            posts = fetch_daily_top(sub)
            posts_by_sub_daily[sub] = sorted(posts, key=lambda p: p["score"], reverse=True)
            print(f"[INFO] {sub}: {len(posts)} posts")
        except Exception as e:
            print(f"[WARN] Failed {sub}: {e}")
            posts_by_sub_daily[sub] = []

    all_daily = [p for posts in posts_by_sub_daily.values() for p in posts]
    all_sorted = sorted(all_daily, key=lambda p: p["score"], reverse=True)

    # DAILY MARKDOWN
    md = build_daily_digest_markdown(date_str, posts_by_sub_daily, ts)
    path = os.path.join(DAILY_DIGEST_DIR, f"reddit_daily_{date_str}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[OK] Daily → {path}")

    weekday = today.weekday()

    # DAILY SOCIAL COPY
    if weekday in SOCIAL_POST_DAYS and all_daily:
        vibe = build_one_line_vibe(all_daily)
        url = build_daily_url(date_str)

        # TWITTER
        tw = build_daily_twitter_thread(date_str, vibe, all_sorted, posts_by_sub_daily, url)
        p = os.path.join(SOCIAL_DIR, f"twitter_thread_{date_str}.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(tw))
        print(f"[OK] Twitter → {p}")

        # LINKEDIN
        li = build_daily_linkedin_post(date_str, vibe, posts_by_sub_daily, url)
        p = os.path.join(SOCIAL_DIR, f"linkedin_post_{date_str}.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(li)
        print(f"[OK] LinkedIn → {p}")

        # POETIC HACKER CAPTION
        cap = f"""🕳️ Reddit Daily – {date_str}

Today felt like code whispering through the cables.

Top threads worth pausing for:
{chr(10).join(f"• r/{p['sub']} – {p['title'][:90]}" for p in all_sorted[:3])}

The pattern is becoming impossible to ignore:
People aren’t chasing hype—they’re soldering ideas in public.
Small models, broken hacks, charts that reveal uncomfortable truths.
It’s messy, brilliant, and weirdly beautiful.

Full digest 👇
{url if url else '🔗 Link in bio'}

#MachineLearning #RedditDaily #AI #Data #OpenSource
"""
        p = os.path.join(SOCIAL_DIR, f"caption_{date_str}.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(cap)
        print(f"[OK] Caption → {p}")
    else:
        print("[INFO] Not a social day")

    # WEEKLY SUPER-CUT
    if weekday == 6 and all_daily:
        posts_by_sub_weekly = {}
        for sub in SUBREDDITS:
            try:
                w = fetch_weekly_top(sub)
                posts_by_sub_weekly[sub] = sorted(w, key=lambda p: p["score"], reverse=True)
                print(f"[INFO] Weekly {sub}: {len(w)} posts")
            except Exception as e:
                print(f"[WARN] Weekly failed {sub}: {e}")
                posts_by_sub_weekly[sub] = []

        all_weekly = [p for posts in posts_by_sub_weekly.values() for p in posts]
        all_weekly_sorted = sorted(all_weekly, key=lambda p: p["score"], reverse=True)
        start = today - datetime.timedelta(days=6)
        label = f"Week of {start} to {today}"

        wk = build_weekly_supercut_markdown(label, posts_by_sub_weekly, ts)
        p = os.path.join(WEEKLY_DIGEST_DIR, f"reddit_weekly_{date_str}.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(wk)
        print(f"[OK] Weekly → {p}")

        if all_weekly:
            url2 = build_weekly_url(date_str, label)

            # TWITTER
            tw = build_weekly_twitter_thread(label, all_weekly_sorted, posts_by_sub_weekly, url2)
            p2 = os.path.join(SOCIAL_DIR, f"twitter_weekly_{date_str}.txt")
            with open(p2, "w", encoding="utf-8") as f:
                f.write("\n\n---\n\n".join(tw))
            print(f"[OK] Weekly Twitter → {p2}")

            # LINKEDIN
            li = build_weekly_linkedin_post(label, posts_by_sub_weekly, url2)
            p2 = os.path.join(SOCIAL_DIR, f"linkedin_weekly_{date_str}.txt")
            with open(p2, "w", encoding="utf-8") as f:
                f.write(li)
            print(f"[OK] Weekly LinkedIn → {p2}")

    # Update RSS + index
    update_rss_feed()
    update_site_index()


if __name__ == "__main__":
    main()