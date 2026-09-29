"""
FeedbackMind — ingest pipeline (core/ingest.py)
CSV + releases.json -> Groq classifies (batched) -> Hindsight retains.
Run from project root:   python -m core.ingest   (add --force to redo)
"""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from . import llm, memory

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BATCH = 8                       # items per Groq call: 173 items = ~22 calls
STATE = DATA / "ingest_state.json"


def load_feedback():
    with open(DATA / "feedback.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_releases():
    return json.loads((DATA / "releases.json").read_text(encoding="utf-8"))


def ingest(force=False):
    if STATE.exists() and not force:
        st = json.loads(STATE.read_text(encoding="utf-8"))
        print(f"Already ingested {st['items']} items at {st['at']}.")
        print("Use --force to redo (e.g. after changing the classifier).")
        return st

    memory.ensure_bank()
    items = load_feedback()
    rels = load_releases()

    print(f"Retaining {len(rels)} product releases...")
    for r in rels:
        memory.store_release(r)

    print(f"Classifying + retaining {len(items)} feedback items "
          f"in batches of {BATCH} (this takes a few minutes)...")
    stats = {}
    for i in range(0, len(items), BATCH):
        batch = items[i:i + BATCH]
        analyses = llm.classify_batch(batch)          # never raises
        for item, an in zip(batch, analyses):
            memory.store_feedback(item, an)
            stats[an["theme"]] = stats.get(an["theme"], 0) + 1
        print(f"  ...{min(i + BATCH, len(items))}/{len(items)} items in memory")

    st = {
        "items": len(items),
        "releases": len(rels),
        "themes": stats,
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")
    print("\n✅ Ingest complete. Themes found:")
    print(json.dumps(stats, indent=2))
    print("\nNext: open https://ui.hindsight.vectorize.io -> bank 'feedbackmind'")
    print("and watch your memories/facts appear. That screenshot = article gold.")
    return st


if __name__ == "__main__":
    try:
        ingest(force="--force" in sys.argv)
    finally:
        memory.client().close()      # close HTTP session cleanly (no warnings)