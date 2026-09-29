"""
FeedbackMind — Hindsight memory wrapper (core/memory.py)
The ONLY place that talks to Hindsight. Memory design:
  * content   = rich natural-language sentence (Hindsight extracts facts from prose)
  * timestamp = the feedback's REAL date -> powers temporal recall ("since v2.3")
  * metadata  = structured analysis for the dashboard (ALL VALUES AS STRINGS)
  * releases retained too -> agent can connect complaints to product changes
"""
import os
import threading
from datetime import datetime

from hindsight_client import Hindsight

BANK = "feedbackmind"
START = datetime(2026, 1, 5)          # week 1 Monday (matches generate_data.py)

MISSION = (
    "You are FeedbackMind, the product-feedback memory of 'Finly', an Indian "
    "fintech app. Remember every piece of customer feedback with its channel, "
    "date and sentiment; remember product releases and their dates; connect "
    "complaints to releases over time; notice which themes grow or shrink."
)

CHANNEL_LABEL = {
    "app_store": "App Store review",
    "support_ticket": "Support ticket",
    "twitter": "Post on X/Twitter",
    "survey": "In-app survey response",
}

_clients = {}


def client():
    """One Hindsight client PER THREAD.

    asyncio/aiohttp objects cannot cross threads, and Streamlit runs every
    script rerun in a fresh thread. Reusing a client from a dead thread
    causes: 'RuntimeError: Timeout context manager should be used inside a
    task'. Per-thread clients fix it completely.
    """
    tid = threading.get_ident()
    if tid not in _clients:
        _clients[tid] = Hindsight(
            base_url=os.environ["HINDSIGHT_BASE_URL"],
            api_key=os.environ["HINDSIGHT_API_KEY"],
        )
    return _clients[tid]

def week_of(d: datetime) -> int:
    return (d - START).days // 7 + 1


def _str_meta(meta: dict) -> dict:
    """Hindsight MemoryItem metadata must be dict[str, str] -> stringify all."""
    return {k: ("" if v is None else str(v)) for k, v in meta.items()}


def ensure_bank():
    """Create the bank once; ignore 'already exists' errors on reruns."""
    try:
        client().create_bank(
            bank_id=BANK,
            name="FeedbackMind",
            mission=MISSION,
            disposition={"skepticism": 4,   # don't over-generalize from 1 complaint
                         "literalism": 3,
                         "empathy": 3},
        )
        print(f"Created bank '{BANK}'")
    except Exception as e:
        print(f"Bank '{BANK}' already exists ({type(e).__name__}) - reusing it")


def store_feedback(item: dict, analysis: dict):
    """Retain ONE feedback item with date, channel, customer + AI analysis."""
    d = datetime.fromisoformat(item["date"])
    try:
        rating = int(item.get("rating") or 0) or None
    except (ValueError, TypeError):
        rating = None
    channel = item["channel"]
    stars = f", {rating} stars" if rating else ""
    content = (f'{CHANNEL_LABEL.get(channel, channel)}{stars} on {item["date"]} '
               f'from {item["customer_name"]} ({item["customer_id"]}): '
               f'"{item["feedback"]}"')
    context = (f"Finly customer feedback, week {week_of(d)}, "
               f"theme {analysis['theme']}, sentiment {analysis['sentiment']}")
    metadata = _str_meta({
        "channel": channel,
        "customer_id": item["customer_id"],
        "rating": rating,
        "week": week_of(d),
        **analysis,
    })
    client().retain(bank_id=BANK, content=content, context=context,
                    timestamp=d, metadata=metadata)


def store_release(rel: dict):
    """Retain a product release as a dated fact (enables before/after reasoning)."""
    d = datetime.fromisoformat(rel["date"])
    content = (f"PRODUCT RELEASE: Finly v{rel['version']} shipped on {rel['date']} - "
               f"{rel['title']}. Changes: {rel['changes']}")
    client().retain(bank_id=BANK, content=content,
                    context="Finly product release log",
                    timestamp=d,
                    metadata=_str_meta({"type": "release",
                                        "version": rel["version"]}))


# ------------------------------------------------------------- read side
def recall(query, budget="mid", types=None):
    kwargs = dict(bank_id=BANK, query=query, budget=budget)
    if types:
        kwargs["types"] = types
    return client().recall(**kwargs)


def reflect(query, context=None):
    return client().reflect(bank_id=BANK, query=query, context=context)


def all_memories(limit=500):
    mems = client().list_memories(bank_id=BANK, limit=limit)
    return getattr(mems, "items", mems)