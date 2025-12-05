![Reddit Daily Banner](banner.png)


<p align="center">

<!-- Build -->
<a href="https://github.com/sukanto-m/reddit-daily/actions">
  <img src="https://img.shields.io/github/actions/workflow/status/sukanto-m/reddit-daily/reddit_daily.yml?label=Daily%20Run&color=blue&logo=github" />
</a>

<!-- RSS -->
<a href="https://sukanto-m.github.io/Reddit-Daily/rss.xml">
  <img src="https://img.shields.io/badge/RSS-Feed-orange?logo=rss" />
</a>

<!-- Python -->
<img src="https://img.shields.io/badge/Python-3.10+-yellow?logo=python" />

<!-- License -->
<img src="https://img.shields.io/badge/License-MIT-green" />

<!-- Last Commit -->
<img src="https://img.shields.io/github/last-commit/sukanto-m/reddit-daily?color=purple" />

<!-- Stars -->
<img src="https://img.shields.io/github/stars/sukanto-m/reddit-daily?style=social" />

</p>






# Reddit Daily  
*A tiny robot that wanders Reddit so you don’t have to.*

Reddit Daily is a lightweight automation that fetches curated posts from your favourite subreddits, compiles them into a neat daily digest, publishes them to GitHub Pages as an RSS-style feed, and—optionally—cross-posts highlight reels to Twitter & LinkedIn twice a week.

Sundays come with a bonus: a weekly **supercut** summarising the whole week’s activity.

Think of it as your personal news-gathering familiar: quiet, consistent, and just a little mischievous.

---

## 🌐 Live Feed
Your human-readable + RSS-friendly feed is published at:

**`https://<your-username>.github.io/Reddit-Daily/rss.xml`**

(This updates automatically whenever the workflow runs.)

---

## ✨ Features

### 📰 Daily Reddit Digest
- Pulls top or hot posts from your selected subreddits.
- Extracts titles, permalinks, timestamps, and summaries.
- Compiles everything into a clean XML feed at `docs/rss.xml`.

### 🚀 Bi-Weekly Social Cross-Posting
- Tweets twice a week (configurable).
- Posts a LinkedIn update twice a week.
- Helps you stay consistent without becoming a “content farm zombie.”

### 🎬 Weekly Supercut Mode
Every Sunday, the bot:
- Scans the last 7 days of collected posts.
- Generates a concise, readable weekly summary.
- Publishes it into your feed as a special edition.

### 💾 Local Logging
- Saves a `cron.log` each run with timestamps and diagnostic information.
- Useful when GitHub Actions acts like it’s had too much coffee.

---

## 📦 Directory Structure

Reddit-Daily/
│
├── docs/
│ ├── index.md # Your HTML/Markdown landing page for GitHub Pages
│ └── rss.xml # Generated RSS-like digest
│
├── config.json # List of subreddits, schedule, posting rules
├── reddit_fetch.py # Core fetcher script
├── social_post.py # Twitter + LinkedIn posting logic
├── weekly_supercut.py # Sunday summariser
├── run_and_publish.sh # Main orchestrator for local testing
│
├── cron.log # Execution logs (ignored by git unless tracked manually)
└── .github/workflows/reddit_daily.yml


---

## ⚙️ Setup

### 1. Clone the Repository
```bash
git clone https://github.com/sukanto-m/reddit-daily
cd reddit-daily

2. Install Dependencies

pip install -r requirements.txt

3. Enable GitHub Pages


Set docs/ as the publishing source.

🛠 Running Locally
Fetch + Publish:
./run_and_publish.sh

Weekly Supercut Only:
python weekly_supercut.py


After each run, check:

docs/rss.xml
docs/index.md
cron.log

🤖 GitHub Actions Workflow

Stored at:

.github/workflows/reddit_daily.yml


It:

Runs daily via cron.

Generates the digest.

Publishes to GitHub Pages.

Runs cross-posting on selected days.

🧠 Troubleshooting
Feed not updating?

Check cron.log for silent errors.

Verify GitHub Pages uses docs/.

Ensure rss.xml is committed.

404 on rss.xml?

Run:

git ls-files docs/rss.xml


If missing:

git add docs/rss.xml
git commit -m "Add RSS feed"
git push

💡 Future Improvements

OP image previews in RSS

Markdown → HTML templating

Topic clustering + sentiment analysis

Auto-archiving to SQLite or DynamoDB

🧵 License

MIT License.
