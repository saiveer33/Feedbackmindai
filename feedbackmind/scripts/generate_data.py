"""
FeedbackMind — Synthetic Data Generator (Phase 1)
Deterministic (seed 42). NO API keys needed.
Run:  python scripts/generate_data.py
Creates: data/feedback.csv + data/releases.json
"""
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent   # project root
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

START = date(2026, 1, 5)          # Monday of week 1
WEEKS = 8

# ---------------------------------------------------------------- customers
FIRST = ["Aarav", "Priya", "Rohit", "Sneha", "Vikram", "Ananya", "Karan",
         "Divya", "Arjun", "Meera", "Rahul", "Kavya", "Suresh", "Nisha",
         "Aditya", "Pooja", "Naveen", "Ishita", "Manoj", "Ritika",
         "Sai", "Deepa", "Varun", "Swathi"]
LAST = ["Reddy", "Sharma", "Patel", "Iyer", "Nair", "Gupta", "Rao",
        "Joshi", "Menon", "Kulkarni", "Singh", "Verma", "Chandra",
        "Murthy", "Bose", "Kapoor"]

# user_101 is our recurring cross-channel complainer
REGULARS = {"user_101": "Rohit Sharma", "user_205": "Priya Iyer",
            "user_304": "Aarav Reddy", "user_509": "Sneha Nair"}

def random_customer():
    if random.random() < 0.18:                     # regulars come back
        cid = random.choice(list(REGULARS))
        return cid, REGULARS[cid]
    cid = f"user_{random.randint(100, 999)}"
    return cid, f"{random.choice(FIRST)} {random.choice(LAST)}"

def day_in_week(week):                              # week is 1-based
    return START + timedelta(days=(week - 1) * 7 + random.randint(0, 6))

# ---------------------------------------------------------------- templates
THEMES = {
    "checkout": {
        "texts": [
            "Checkout page takes forever to load and the UPI payment times out half the time.",
            "Tried paying 3 times at checkout. Each time it said 'payment processing' and then failed. Money not deducted, thank god, but so frustrating.",
            "Why is checkout so slow?? Every other app is instant. Lost a customer today.",
            "UPI payment at checkout failed again with error UPI-99. This has been happening for weeks.",
            "Checkout keeps timing out on mobile data. Works on wifi sometimes. Please fix.",
            "Payment page hangs at the final step. Had to switch to another app to complete my transaction.",
            "Checkout is extremely slow today. Is anyone else seeing this?",
        ],
        "channels": {"app_store": 4, "support_ticket": 4, "twitter": 3, "survey": 1},
        "rating": (1, 2),
    },
    "dashboard": {
        "texts": [
            "Ever since the last update the dashboard takes 10+ seconds to load. Uninstalling if not fixed.",
            "New update ruined the speed. Dashboard barely opens. What happened?",
            "The redesigned dashboard is beautiful but SO slow. Loading spinner is my new best friend.",
            "Dashboard crashes when I open the transactions tab. Started after v2.3.",
            "App update made everything sluggish - home screen, dashboard, statements. Please rollback.",
            "Love the fresh look of the new dashboard, honestly. But the loading times are terrible.",
            "Dashboard still slow this week. Third time reporting it.",
        ],
        "channels": {"app_store": 5, "support_ticket": 2, "twitter": 3, "survey": 2},
        "rating": (1, 3),
    },
    "search": {
        "texts": [
            "Search inside the app is useless. Typing 'electricity bill' shows nothing relevant.",
            "The search feature is so slow, results take 5-6 seconds and half of them are wrong.",
            "Cannot find old transactions through search. Filters are impossible to locate.",
            "Search returns irrelevant results. I type a payee name and get random stuff.",
            "Your search bar timed out twice today. How hard is it to search transactions?!",
            "New search is broken - shows 'no results' for payments that definitely exist.",
            "Search performance is getting worse every week. Switching to the other app.",
        ],
        "channels": {"app_store": 3, "support_ticket": 4, "twitter": 2, "survey": 2},
        "rating": (1, 3),
    },
    "ui_praise": {
        "texts": [
            "The new design looks premium! Finally an Indian fintech app that feels modern.",
            "Redesign is gorgeous. Dark mode is perfect. Great job team!",
            "Updated yesterday - the new UI is clean and easy to navigate. Five stars from me.",
            "Loving the fresh look. My parents can finally use the app without calling me.",
        ],
        "channels": {"app_store": 4, "twitter": 4, "survey": 3, "support_ticket": 1},
        "rating": (4, 5),
    },
    "support_praise": {
        "texts": [
            "Support team resolved my issue in 10 minutes on chat. Impressed!",
            "Your support agent Deepika was incredibly patient and helpful. Give her a raise.",
            "Raised a ticket at 11pm, got a proper resolution by morning. Good service.",
        ],
        "channels": {"survey": 4, "twitter": 3, "app_store": 3, "support_ticket": 1},
        "rating": (4, 5),
    },
    "pricing": {
        "texts": [
            "New premium pricing is steep for what you get. Other apps give this free.",
            "Why am I now being charged for the statements feature? That used to be free.",
            "Pricing plan confusion - got billed for premium but I never subscribed.",
        ],
        "channels": {"app_store": 3, "twitter": 3, "survey": 2, "support_ticket": 2},
        "rating": (2, 3),
    },
    "login_otp": {
        "texts": [
            "OTP never arrives on my number during evenings. Locked out again.",
            "Login keeps failing with 'session expired' even right after signup.",
            "Biometric login stopped working after the update. PIN every time now.",
        ],
        "channels": {"support_ticket": 4, "app_store": 3, "twitter": 2, "survey": 1},
        "rating": (1, 3),
    },
    "notifications": {
        "texts": [
            "Getting 8 notification a day for offers. Please add a mute option.",
            "Payment success notifications are delayed by hours. Confusing when reconciling.",
        ],
        "channels": {"app_store": 3, "survey": 3, "twitter": 2, "support_ticket": 1},
        "rating": (2, 4),
    },
    "misc": {
        "texts": [
            "App is fine overall. Does what it says.",
            "Works okay for daily UPI payments. Nothing spectacular.",
            "Would love a widget for quick pay on the home screen.",
            "Add an option to schedule recurring payments please!",
            "Decent app but the icon looks dated on my phone.",
        ],
        "channels": {"app_store": 3, "survey": 3, "twitter": 2, "support_ticket": 1},
        "rating": (3, 5),
    },
}

# weekly counts per theme = the STORY
#        w1 w2 w3 w4 w5 w6 w7 w8   events: v2.3 lands Jan 20 (wk3),
PLAN = {                            #         v2.4 lands Feb 17 (wk7)
    "checkout":      [4, 5, 5, 6, 6, 7, 8, 9],   # 1) recurring, growing
    "dashboard":     [1, 2, 6, 9, 8, 7, 3, 2],   # 2) spikes after v2.3, fixed by v2.4
    "search":        [1, 1, 2, 2, 5, 8, 12, 16], # 3) EMERGING in weeks 5-8
    "ui_praise":     [1, 1, 4, 5, 4, 3, 3, 3],   # v2.3 redesign looked great
    "support_praise":[2, 1, 2, 2, 1, 2, 2, 2],
    "pricing":       [1, 1, 1, 2, 1, 1, 2, 1],
    "login_otp":     [1, 2, 1, 1, 2, 1, 1, 2],
    "notifications": [1, 0, 1, 1, 0, 1, 1, 1],
    "misc":          [2, 2, 2, 1, 2, 2, 1, 2],
}

# user_101's scripted cross-channel journey (pattern 4)
SCRIPTED = [
    (1, "app_store",      "user_101", "Rohit Sharma",
     "Checkout was slow today during my metro commute. UPI payment timed out twice.", 2),
    (3, "support_ticket", "user_101", "Rohit Sharma",
     "Reporting again: checkout UPI payment fails on mobile data. Ticket #4471. This is the third time this month.", 1),
    (5, "twitter",        "user_101", "Rohit Sharma",
     "@FinlyApp checkout still broken in 2026?? Third complaint, still no fix. Moving my salary account if this continues.", 1),
    (7, "support_ticket", "user_101", "Rohit Sharma",
     "Checkout timeouts continue even after the v2.4 update. Other issues fixed, this one not. Ticket #5120.", 2),
]

def pick_channel(weights):
    chans = list(weights.keys())
    ws = list(weights.values())
    return random.choices(chans, weights=ws, k=1)[0]

def main():
    rows = []

    # scripted cross-channel journey first
    for week, ch, cid, name, text, rating in SCRIPTED:
        rows.append({"date": day_in_week(week).isoformat(), "channel": ch,
                     "customer_id": cid, "customer_name": name,
                     "feedback": text, "rating": rating})

    seen = set()
    for theme, counts in PLAN.items():
        spec = THEMES[theme]
        for week, n in enumerate(counts, start=1):
            for _ in range(n):
                text = random.choice(spec["texts"])
                key = (week, text)
                if key in seen and random.random() < 0.7:
                    continue                     # avoid too many exact dupes
                seen.add(key)
                cid, name = random_customer()
                lo, hi = spec["rating"]
                rows.append({
                    "date": day_in_week(week).isoformat(),
                    "channel": pick_channel(spec["channels"]),
                    "customer_id": cid,
                    "customer_name": name,
                    "feedback": text,
                    "rating": random.randint(lo, hi),
                })

    rows.sort(key=lambda r: r["date"])

    out = DATA / "feedback.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "channel", "customer_id",
                                          "customer_name", "feedback", "rating"])
        w.writeheader()
        w.writerows(rows)

    releases = [
        {"version": "2.2", "date": "2025-12-08",
         "title": "Year-end release",
         "changes": "Year-in-review statements page; minor bug fixes; festival offer banners."},
        {"version": "2.3", "date": "2026-01-20",
         "title": "Dashboard Redesign",
         "changes": "Completely redesigned dashboard UI with dark mode, new visual style, and reworked transactions tab."},
        {"version": "2.4", "date": "2026-02-17",
         "title": "Performance Update",
         "changes": "Dashboard load-time optimizations, fixed transactions-tab crash, faster home screen rendering. Search backend NOT touched in this release."},
    ]
    with open(DATA / "releases.json", "w", encoding="utf-8") as f:
        json.dump(releases, f, indent=2)

    # ---- summary so you can SEE the buried patterns ----
    print(f"Wrote {len(rows)} feedback items -> {out}")
    print(f"Wrote {len(releases)} releases   -> {DATA / 'releases.json'}")
    from collections import Counter
    per_week = Counter()
    for r in rows:
        d = date.fromisoformat(r["date"])
        per_week[(d - START).days // 7 + 1] += 1
    print("\nItems per week:", dict(sorted(per_week.items())))
    print("\nStory check (should match the plan):")
    print("  - dashboard complaints spike weeks 3-6, drop weeks 7-8")
    print("  - search complaints explode weeks 5-8")
    print("  - checkout complaints grow steadily all 8 weeks")
    print("  - user_101 appears in app_store + support_ticket + twitter")

if __name__ == "__main__":
    main()