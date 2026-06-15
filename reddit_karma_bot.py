import os
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ── Config ─────────────────────────────────────────────────────────────────
BOT_TOKEN   = os.environ.get("BOT_TOKEN",   "8494074116:AAGUStzYTDlwgxhj1T2yx0HHRsrerw8WXIc")
CHAT_ID     = os.environ.get("CHAT_ID",     "8000091887")
GEMINI_KEY  = os.environ.get("GEMINI_KEY",  "AQ.Ab8RN6JKTKc0VANDAXlYqldZONIZA7Y4eA2LeGU0ZPCerF7hVQ")

SUBREDDITS = ["gurgaon", "CarsIndia", "PataHaiAajKyaHua"]

SEND_DAYS    = [0, 3]   # Monday=0, Thursday=3
SEND_HOUR    = 9        # 9 AM IST

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RSS-Reader/1.0)"}

# ── Telegram ───────────────────────────────────────────────────────────────
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
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

# ── RSS Fetcher (no API key needed!) ──────────────────────────────────────
def fetch_posts_rss(subreddit: str, limit=15):
    """Fetch posts via Reddit's public RSS feed — works from any server."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.rss?limit={limit}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()

        # Parse RSS XML
        root = ET.fromstring(r.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)

        posts = []
        for entry in entries:
            title   = entry.findtext("atom:title", default="", namespaces=ns).strip()
            link_el = entry.find("atom:link", ns)
            url_    = link_el.get("href", "") if link_el is not None else ""
            content = entry.findtext("atom:content", default="", namespaces=ns)
            updated = entry.findtext("atom:updated", default="", namespaces=ns)

            if title and url_ and "reddit.com" in url_:
                posts.append({
                    "title":   title,
                    "url":     url_,
                    "content": content[:300] if content else "",
                    "date":    updated[:10] if updated else "",
                })

        print(f"[{now()}] r/{subreddit}: got {len(posts)} posts via RSS")
        return posts

    except Exception as e:
        print(f"[{now()}] RSS fetch failed for r/{subreddit}: {e}")
        return []

# ── Gemini AI ──────────────────────────────────────────────────────────────
def ask_gemini(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    try:
        r = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.85, "maxOutputTokens": 1800}
        }, timeout=30)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[{now()}] Gemini error: {e}")
        return "⚠️ Gemini analysis failed. Try again later."

# ── Analyzer ───────────────────────────────────────────────────────────────
def analyze_subreddit(subreddit: str):
    posts = fetch_posts_rss(subreddit)
    if not posts:
        return None

    posts_summary = ""
    for i, p in enumerate(posts[:10], 1):
        posts_summary += f"{i}. {p['title']} (Posted: {p['date']})\n"

    top_post = posts[0] if posts else None

    prompt = f"""
You are a Reddit growth expert helping someone build karma in r/{subreddit}.

Here are the current hot posts in this subreddit:

{posts_summary}

Based on this data, provide:

1. COMMUNITY VIBE (2 sentences): What tone and topics work here?

2. TRENDS: What 3 themes are getting traction right now?

3. POST 1 — Write a complete ready-to-post Reddit post (title + body) that fits this community perfectly. Make it authentic, relatable, not promotional.

4. POST 2 — Write a second completely different post (different format or angle). 

5. BEST TIME: Best day and time to post in IST for maximum visibility.

6. PRO TIP: One specific tip to maximize karma in this subreddit.

Use these exact headers:
VIBE:
TRENDS:
POST 1:
POST 2:
BEST TIME:
PRO TIP:

For r/PataHaiAajKyaHua use Hindi/Hinglish naturally. Keep posts conversational and genuine.
"""
    print(f"[{now()}] Asking Gemini for r/{subreddit}...")
    analysis = ask_gemini(prompt)
    return {"subreddit": subreddit, "analysis": analysis, "top_post": top_post}

# ── Report ─────────────────────────────────────────────────────────────────
def build_and_send_report():
    print(f"[{now()}] Building karma report...")
    send_telegram("🧠 <b>Reddit Karma Report</b>\n\nAnalyzing your 3 communities... ~1 minute ⏳")

    for subreddit in SUBREDDITS:
        result = analyze_subreddit(subreddit)
        if not result:
            send_telegram(f"⚠️ Could not analyze r/{subreddit}. Skipping.")
            continue

        top = result["top_post"]
        top_ref = ""
        if top:
            top_ref = (
                f"\n📌 <b>Top Post Right Now:</b>\n"
                f"<i>{top['title']}</i>\n"
                f"🔗 {top['url']}\n"
            )

        message = (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>r/{subreddit}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
            f"{top_ref}\n"
            f"🤖 <b>Gemini Analysis:</b>\n\n"
            f"{result['analysis']}"
        )
        send_telegram(message)
        time.sleep(2)

    send_telegram(
        "✅ <b>Report complete!</b>\n\n"
        "📅 You have <b>2 post slots this week</b>.\n"
        "Pick the best ideas above and post on the suggested days.\n\n"
        "Next report: Monday or Thursday at 9 AM IST 🔄"
    )

# ── Scheduler ──────────────────────────────────────────────────────────────
def should_run_now():
    now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    return now_ist.weekday() in SEND_DAYS and now_ist.hour == SEND_HOUR

def now():
    return datetime.now().strftime("%H:%M:%S")

# ── Main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  Reddit Karma Bot — RSS Edition")
    print(f"  Subreddits : {', '.join('r/'+s for s in SUBREDDITS)}")
    print(f"  Schedule   : Monday & Thursday at 9 AM IST")
    print("=" * 50)

    send_telegram(
        "🚀 <b>Reddit Karma Bot is LIVE!</b>\n\n"
        f"👀 Monitoring: <b>r/{' | r/'.join(SUBREDDITS)}</b>\n"
        "📅 Reports every <b>Monday & Thursday at 9 AM IST</b>\n"
        "✍️ 2 ready-to-post drafts per community per report\n\n"
        "Sending first report now... 🔄"
    )

    # Run immediately on start
    build_and_send_report()

    last_run_date = datetime.utcnow().date()
    while True:
        time.sleep(3600)
        today = datetime.utcnow().date()
        if should_run_now() and today != last_run_date:
            build_and_send_report()
            last_run_date = today
