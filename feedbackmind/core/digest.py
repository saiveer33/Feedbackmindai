"""
FeedbackMind — weekly digest engine + learning loop (core/digest.py)

  python -m core.digest 2        generate week 2's digest
  python -m core.digest pm 2 "Focus only on revenue-impacting themes..."
  python -m core.digest 6        a later digest -> visibly follows the correction
  python -m core.digest seed     fill weeks 1-8 (injects a correction after wk 2)

LEARNING LOOP: every digest AND every PM correction is retained back into
Hindsight as an *experience fact*, so reflect() retrieves them next time
and the digests visibly improve. Digests are also mirrored to
data/digests.json so the UI can show a timeline without extra recalls.
"""
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from . import llm, memory

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DIGESTS_FILE = DATA / "digests.json"
STATE = DATA / "digest_state.json"

DEFAULT_CORRECTION = (
    "Stop listing minor login/OTP noise. Focus only on themes that impact "
    "revenue (checkout, search, dashboard). Always compare sentiment against "
    "the most recent product release, and end with exactly two prioritized "
    "recommendations."
)


# ---------------------------------------------------------------- helpers
def week_range(week):
    start = memory.START + timedelta(days=(week - 1) * 7)
    return start, start + timedelta(days=6)


def _load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _pm_instructions():
    """Retrieve the PM's standing corrections from memory (experience facts)."""
    try:
        res = memory.recall("PM standing instructions and corrections for the weekly digests",
                            types=["experience"], budget="low")
        return [r.text for r in res.results[:5]]
    except Exception:
        return []


# ---------------------------------------------------------------- trends
def theme_week_counts():
    """Weekly mention counts per theme, read straight from memory metadata."""
    counts = {}
    for m in memory.all_memories(limit=1000):
        md = getattr(m, "metadata", None) or {}
        theme, week = md.get("theme"), md.get("week")
        if not theme or not week:
            continue
        counts.setdefault(theme, Counter())[int(week)] += 1
    return counts


def emerging_issues(early_weeks=(1, 2, 3, 4), late_weeks=(5, 6, 7, 8),
                    min_late=12, min_growth=1.8):
    """Themes whose mentions accelerate in the late window = emerging issues."""
    alerts = []
    for theme, wk in theme_week_counts().items():
        early = sum(wk.get(w, 0) for w in early_weeks)
        late = sum(wk.get(w, 0) for w in late_weeks)
        growth = late / max(early, 1)
        if late >= min_late and growth >= min_growth:
            alerts.append({"theme": theme, "early": early, "late": late,
                           "growth": round(growth, 2),
                           "per_week": [wk.get(w, 0) for w in range(1, 9)]})
    alerts.sort(key=lambda a: a["growth"], reverse=True)
    return alerts


# ---------------------------------------------------------------- digests
def generate_digest(week):
    start, end = week_range(week)
    pm_notes = _pm_instructions()
    pm_block = ("\nPM standing instructions you MUST follow:\n- "
                + "\n- ".join(pm_notes)) if pm_notes else ""
    query = (
        f"Write the weekly product-feedback digest for Finly covering only "
        f"feedback between {start:%b %d %Y} and {end:%b %d %Y}. Include: "
        f"(1) top themes with concrete evidence, (2) sentiment direction versus "
        f"earlier weeks, (3) any emerging or resolving issue, (4) how the most "
        f"recent product release affected feedback. Then give prioritized "
        f"recommendations.{pm_block}"
    )
    ans = memory.reflect(query, context=f"FeedbackMind weekly digest, week {week}")
    text = ans.text

    # 1) retain the digest INTO memory (experience fact) -> agent builds on it
    memory.client().retain(
        bank_id=memory.BANK,
        content=f"FeedbackMind weekly digest, week {week} ({start:%Y-%m-%d}): {text}",
        context="FeedbackMind's own past analysis",
        timestamp=end,
        metadata={"type": "digest", "week": str(week)},
    )
    # 2) mirror to JSON for the UI timeline
    digests = _load_json(DIGESTS_FILE, {})
    digests[str(week)] = {"text": text, "week_start": start.isoformat(),
                          "pm_instructions_applied": len(pm_notes)}
    DIGESTS_FILE.write_text(json.dumps(digests, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    # 3) mark week done
    st = _load_json(STATE, {"weeks": []})
    if week not in st["weeks"]:
        st["weeks"].append(week)
        STATE.write_text(json.dumps(st), encoding="utf-8")
    return text


def record_pm_feedback(week, comment):
    """The learning step: PM correction becomes an experience fact."""
    memory.client().retain(
        bank_id=memory.BANK,
        content=f"PM feedback on week {week} digest: {comment}",
        context="Product manager's standing correction for FeedbackMind digests",
        timestamp=datetime.now(),
        metadata={"type": "pm_feedback", "week": str(week)},
    )
    return f"Recorded PM correction for week {week}. Future digests will follow it."


def seed():
    """One-command demo state: digests for weeks 1-8, correction after week 2."""
    st = _load_json(STATE, {"weeks": []})
    for w in range(1, 9):
        if w in st["weeks"]:
            print(f"week {w}: already digested, skipping")
            continue
        print(f"--- digest week {w} ---")
        print(generate_digest(w)[:400], "...\n")
        if w == 2:
            print(">>> injecting PM correction:", DEFAULT_CORRECTION, "\n")
            record_pm_feedback(2, DEFAULT_CORRECTION)
    print("✅ Digest timeline complete (weeks 1-8). Learning loop armed.")


# ---------------------------------------------------------------- CLI
if __name__ == "__main__":
    argv = sys.argv[1:]
    try:
        if not argv:
            print(__doc__)
        elif argv[0] == "pm":
            print(record_pm_feedback(int(argv[1]), " ".join(argv[2:])))
        elif argv[0] == "seed":
            seed()
        else:
            out = generate_digest(int(argv[0]))
            print(f"\n================ WEEK {argv[0]} DIGEST ================\n")
            print(out)
    finally:
        memory.client().close()