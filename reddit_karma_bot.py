import os
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ── Config ─────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN",  "8494074116:AAGUStzYTDlwgxhj1T2yx0HHRsrerw8WXIc")
CHAT_ID    = os.environ.get("CHAT_ID",    "8000091887")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "AQ.Ab8RN6JKTKc0VANDAXlYqldZONIZA7Y4eA2LeGU0ZPCerF7hVQ")

SUBREDDITS = ["gurgaon", "CarsIndia", "PataHaiAajKyaHua"]
SEND_DAYS  = [0, 3]   # Monday, Thursday
SEND_HOUR  = 9        # 9 AM IST

# Rotate user agents to avoid Reddit blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
]

import random
def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
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

# ── Reddit RSS Fetcher ─────────────────────────────────────────────────────
def fetch_posts_rss(subreddit):
    urls_to_try = [
        f"https://www.reddit.com/r/{subreddit}/hot.rss?limit=15",
        f"https://old.reddit.com/r/{subreddit}/hot.rss?limit=15",
        f"https://reddit.com/r/{subreddit}/.rss?limit=15",
    ]
    for url in urls_to_try:
        try:
            time.sleep(2)  # polite delay between requests
            r = requests.get(url, headers=get_headers(), timeout=20)
            if r.status_code == 429:
                print(f"[{now()}] Rate limited on {url}, trying next...")
                time.sleep(5)
                continue
            r.raise_for_status()
            root = ET.fromstring(r.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            posts = []
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", default="", namespaces=ns).strip()
                link  = entry.find("atom:link", ns)
                url_  = link.get("href", "") if link is not None else ""
                date  = entry.findtext("atom:updated", default="", namespaces=ns)[:10]
                if title and url_ and "reddit.com" in url_:
                    posts.append({"title": title, "url": url_, "date": date})
            if posts:
                print(f"[{now()}] r/{subreddit}: {len(posts)} posts fetched ✅")
                return posts
        except Exception as e:
            print(f"[{now()}] Failed {url}: {e}")
            continue
    # Final fallback — use Gemini to generate based on subreddit knowledge
    print(f"[{now()}] r/{subreddit}: All RSS attempts failed, using Gemini fallback")
    return []

# ── Gemini AI ──────────────────────────────────────────────────────────────
def ask_gemini(prompt):
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
        return "⚠️ Gemini analysis unavailable right now."

# ── Analyzer ───────────────────────────────────────────────────────────────
def analyze_and_send(subreddit):
    posts = fetch_posts_rss(subreddit)

    if posts:
        summary = "\n".join([f"{i+1}. {p['title']} ({p['date']})" for i, p in enumerate(posts[:10])])
        prompt = f"""You are a Reddit growth expert helping someone build karma in r/{subreddit}.

Here are the current hot posts:

{summary}

Provide exactly this, with these headers:

VIBE: (2 sentences about what tone and topics work in this community)

TRENDS: (3 bullet points of what themes are trending right now)

POST 1 TITLE: (a complete catchy post title)
POST 1 BODY: (2-4 paragraph authentic post body, ready to copy-paste)

POST 2 TITLE: (a completely different post title)
POST 2 BODY: (2-4 paragraph authentic post body, ready to copy-paste)

BEST TIME: (best day and time to post in IST for max visibility)

PRO TIP: (one specific actionable tip for this subreddit)

Rules: Be authentic, not promotional. For r/PataHaiAajKyaHua use Hindi/Hinglish naturally. Make posts feel human and relatable."""

        top = posts[0]
        top_ref = f"\n📌 <b>Top Post Now:</b> <i>{top['title']}</i>\n🔗 {top['url']}\n"
    else:
        # Gemini fallback when RSS is blocked
        prompt = f"""You are a Reddit growth expert helping someone build karma in r/{subreddit}.

You don't have live data right now, but based on your knowledge of this subreddit, provide:

VIBE: (2 sentences about what tone and topics work in this community)

TRENDS: (3 bullet points of typical trending themes in this subreddit)

POST 1 TITLE: (a complete catchy post title that would do well)
POST 1 BODY: (2-4 paragraph authentic post body, ready to copy-paste)

POST 2 TITLE: (a completely different post title)
POST 2 BODY: (2-4 paragraph authentic post body, ready to copy-paste)

BEST TIME: (best day and time to post in IST for max visibility)

PRO TIP: (one specific actionable tip for this subreddit)

Rules: Be authentic and specific to this community. For r/PataHaiAajKyaHua use Hindi/Hinglish. Make posts feel human."""
        top_ref = "\n⚠️ <i>Live data unavailable — Gemini using community knowledge</i>\n"

    analysis = ask_gemini(prompt)

    send_telegram(
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>r/{subreddit}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
        f"{top_ref}\n"
        f"🤖 <b>Gemini Analysis:</b>\n\n{analysis}"
    )

# ── Report builder ─────────────────────────────────────────────────────────
def build_report():
    print(f"[{now()}] 📊 Building karma report...")
    send_telegram("🧠 <b>Reddit Karma Report</b>\n\nAnalyzing your 3 communities... ⏳ ~2 minutes")
    for subreddit in SUBREDDITS:
        analyze_and_send(subreddit)
        time.sleep(3)
    send_telegram(
        "✅ <b>Report complete!</b>\n\n"
        "📅 You have <b>2 post slots this week</b>\n"
        "Pick the best drafts above and post on suggested days\n\n"
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
    print("=" * 50)
    print("  Reddit Karma Bot — RSS + Gemini Fallback")
    print(f"  Subreddits : {', '.join('r/'+s for s in SUBREDDITS)}")
    print(f"  Schedule   : Monday & Thursday at 9 AM IST")
    print("=" * 50)

    send_telegram(
        "🚀 <b>Reddit Karma Bot is LIVE!</b>\n\n"
        f"👀 Monitoring: <b>r/{' | r/'.join(SUBREDDITS)}</b>\n"
        "📅 Reports every <b>Monday & Thursday at 9 AM IST</b>\n"
        "✍️ 2 ready-to-post drafts per community\n\n"
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
