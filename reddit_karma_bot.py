import os
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import random

# ── Config ─────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN",  "8494074116:AAGUStzYTDlwgxhj1T2yx0HHRsrerw8WXIc")
CHAT_ID    = os.environ.get("CHAT_ID",    "8000091887")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "AQ.Ab8RN6KhomwjIOAquuB0vIbzihDwmrJCtpVQgC8d2XtyI47LOw")

SUBREDDITS = ["gurgaon", "CarsIndia", "PataHaiAajKyaHua"]
SEND_DAYS  = [0, 3]   # Monday=0, Thursday=3
SEND_HOUR  = 9        # 9 AM IST

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }

# ── Telegram ───────────────────────────────────────────────────────────────
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for chunk in [message[i:i+4000] for i in range(0, len(message), 4000)]:
        try:
            r = requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }, timeout=10)
            r.raise_for_status()
            time.sleep(0.5)
        except Exception as e:
            print(f"[{now()}] Telegram error: {e}")

# ── Reddit RSS ─────────────────────────────────────────────────────────────
def fetch_posts_rss(subreddit):
    urls_to_try = [
        f"https://www.reddit.com/r/{subreddit}/hot.rss?limit=20",
        f"https://old.reddit.com/r/{subreddit}/hot.rss?limit=20",
    ]
    for url in urls_to_try:
        try:
            time.sleep(3)
            r = requests.get(url, headers=get_headers(), timeout=20)
            if r.status_code == 429:
                time.sleep(10)
                continue
            r.raise_for_status()
            root = ET.fromstring(r.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            posts = []
            for entry in root.findall("atom:entry", ns):
                title   = entry.findtext("atom:title", default="", namespaces=ns).strip()
                link_el = entry.find("atom:link", ns)
                url_    = link_el.get("href", "") if link_el is not None else ""
                date    = entry.findtext("atom:updated", default="", namespaces=ns)[:10]
                if title and url_ and "reddit.com" in url_:
                    posts.append({"title": title, "url": url_, "date": date})
            if posts:
                print(f"[{now()}] r/{subreddit}: {len(posts)} posts ✅")
                return posts
        except Exception as e:
            print(f"[{now()}] RSS failed for r/{subreddit}: {e}")
    print(f"[{now()}] r/{subreddit}: RSS blocked, using Gemini knowledge")
    return []

# ── Gemini ─────────────────────────────────────────────────────────────────
def ask_gemini(prompt):
    # Support both old (AIzaSy) and new (AQ.) key formats
    models = ["gemini-1.5-flash", "gemini-pro"]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        try:
            r = requests.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.85,
                    "maxOutputTokens": 2000
                }
            }, timeout=40)
            if r.status_code == 400:
                print(f"[{now()}] Model {model} failed, trying next...")
                continue
            r.raise_for_status()
            result = r.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            print(f"[{now()}] Gemini responded via {model} ✅")
            return text
        except Exception as e:
            print(f"[{now()}] Gemini error with {model}: {e}")
            continue
    return None

# ── Core Logic ─────────────────────────────────────────────────────────────
def build_report():
    print(f"[{now()}] Building smart karma report...")
    send_telegram("🧠 <b>Reddit Karma Report</b>\n\nAnalyzing all 3 communities to find your best 2 posts this week... ⏳")

    # Step 1: Fetch all subreddit data
    all_data = {}
    for subreddit in SUBREDDITS:
        posts = fetch_posts_rss(subreddit)
        all_data[subreddit] = posts
        time.sleep(2)

    # Step 2: Build combined summary for Gemini
    combined = ""
    for subreddit, posts in all_data.items():
        combined += f"\n### r/{subreddit}\n"
        if posts:
            for i, p in enumerate(posts[:8], 1):
                combined += f"{i}. {p['title']} ({p['date']})\n"
        else:
            combined += "Live data unavailable — use your knowledge of this community\n"

    # Step 3: Ask Gemini to pick the BEST 2 opportunities across all communities
    prompt = f"""You are a Reddit growth expert. Someone wants to build karma across these 3 Indian subreddits:
- r/gurgaon (Gurgaon city community — local news, experiences, recommendations)
- r/CarsIndia (Indian car enthusiasts — reviews, photos, opinions, comparisons)  
- r/PataHaiAajKyaHua (Hindi/Hinglish memes and trending Indian news)

Here are the current trending posts in each community:

{combined}

Your job: Identify the TOP 2 posting opportunities this week across ALL communities combined.
Choose communities where engagement potential is highest RIGHT NOW based on the trends.
It's okay to pick 2 from the same community if that's where the opportunity is.

For each opportunity provide:

---
OPPORTUNITY 1:
COMMUNITY: r/[subreddit name]
WHY THIS COMMUNITY NOW: (1-2 sentences on why this is the best bet right now)
ENGAGEMENT SCORE: [High/Very High/Exceptional] — explain why in one line
POST TITLE: (exact title ready to copy-paste)
POST BODY: (complete post body, 2-4 paragraphs, ready to copy-paste, authentic and conversational)
BEST TIME TO POST: (specific day + time in IST)
QUICK TIP: (one specific tip to maximize upvotes for this post)

---
OPPORTUNITY 2:
COMMUNITY: r/[subreddit name]
WHY THIS COMMUNITY NOW: (1-2 sentences)
ENGAGEMENT SCORE: [High/Very High/Exceptional] — explain why
POST TITLE: (exact title ready to copy-paste)
POST BODY: (complete post body, 2-4 paragraphs, ready to copy-paste)
BEST TIME TO POST: (specific day + time in IST)
QUICK TIP: (one specific tip)

---
WEEKLY STRATEGY: (2-3 sentences on the overall approach this week)

Rules:
- For r/PataHaiAajKyaHua use natural Hindi/Hinglish
- Posts must feel 100% human, not AI-written
- Base recommendations on what's actually trending in the data above
- Be specific and actionable
- Do NOT recommend promotional content"""

    analysis = ask_gemini(prompt)

    if not analysis:
        send_telegram(
            "⚠️ <b>Gemini API issue</b>\n\n"
            "The AI analysis failed. Please check your GEMINI_KEY in Railway variables.\n"
            "Make sure it's the correct key from aistudio.google.com/apikey"
        )
        return

    # Step 4: Send clean report
    # Add top post references
    top_posts_ref = ""
    for subreddit, posts in all_data.items():
        if posts:
            top_posts_ref += f"📌 r/{subreddit}: <i>{posts[0]['title']}</i>\n🔗 {posts[0]['url']}\n\n"

    if top_posts_ref:
        send_telegram(f"📊 <b>Current Top Posts (for context):</b>\n\n{top_posts_ref}")

    send_telegram(f"🎯 <b>Your 2 Best Posts This Week:</b>\n\n{analysis}")

    send_telegram(
        "✅ <b>Done!</b>\n\n"
        "👆 Pick your 2 posts above and schedule them on the suggested days.\n"
        "🔄 Next report: Monday or Thursday at 9 AM IST"
    )

# ── Scheduler ──────────────────────────────────────────────────────────────
def should_run():
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    return ist.weekday() in SEND_DAYS and ist.hour == SEND_HOUR

def now():
    return datetime.now().strftime("%H:%M:%S")

# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  Reddit Karma Bot — Smart Edition")
    print(f"  Subreddits : {', '.join('r/'+s for s in SUBREDDITS)}")
    print(f"  Schedule   : Monday & Thursday at 9 AM IST")
    print("=" * 55)

    send_telegram(
        "🚀 <b>Reddit Karma Bot is LIVE!</b>\n\n"
        f"👀 Watching: <b>r/{' | r/'.join(SUBREDDITS)}</b>\n"
        "📅 Reports: <b>Monday & Thursday at 9 AM IST</b>\n"
        "🎯 Picks only the <b>TOP 2 opportunities</b> per week\n\n"
        "Sending first report now... 🔄"
    )

    build_report()

    last = datetime.utcnow().date()
    while True:
        time.sleep(3600)
        today = datetime.utcnow().date()
        if should_run() and today != last:
            build_report()
            last = today
