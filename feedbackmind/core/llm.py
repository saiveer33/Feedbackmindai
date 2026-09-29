"""
FeedbackMind — Groq LLM wrapper (core/llm.py)
The ONLY place that talks to Groq. Everything else calls classify_batch().
Defenses: auto model pick -> JSON mode -> retry -> salvage JSON -> heuristic.
"""
import json
import os
import re

from groq import Groq

# Groq retires/renames models often, so we auto-pick the best model your API
# key can actually access right now (see pick_model()). .env can still
# request a specific model - it gets first priority.
PREFERRED_MODELS = [
    os.environ.get("GROQ_MODEL", ""),      # whatever .env asks for
    "openai/gpt-oss-120b",                 # hackathon-recommended
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]

MODEL = None

_client = None


def client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


def pick_model():
    """Ask Groq which models exist right now; choose the first preferred one."""
    global MODEL
    if MODEL:
        return MODEL
    try:
        available = {m.id for m in client().models.list()}
    except Exception:
        available = set()
    for cand in PREFERRED_MODELS:
        if cand and (cand in available or not available):
            MODEL = cand
            break
    else:
        MODEL = sorted(available)[0] if available else PREFERRED_MODELS[1]
    print(f"[llm] using model: {MODEL}")
    return MODEL


THEMES = ("checkout_payments", "dashboard_performance", "search", "ui_design",
          "pricing", "login_otp", "notifications", "support_experience", "other")

SYSTEM = (
    "You are the analysis engine of FeedbackMind, a product-feedback memory "
    "agent for 'Finly', an Indian fintech mobile app (UPI payments, checkout, "
    "dashboard, search, statements).\n"
    "Classify every feedback item precisely.\n"
    "Output ONLY valid JSON of this exact shape:\n"
    '{"results": [{"idx": 1, "sentiment": "positive|negative|neutral", '
    '"theme": "<one of: ' + "|".join(THEMES) + '>", '
    '"feature": "<short product area, e.g. UPI checkout>", '
    '"severity": "low|medium|high", "summary": "<one-sentence gist>"}]}\n'
    "One object per input item, in the same order as the input."
)


# ------------------------------------------------------------- JSON parsing
def _parse_results(raw, n):
    """Extract a list of n analyses from a (possibly messy) model reply."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)          # salvage the JSON block
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    if isinstance(data, dict):
        for key in ("results", "items", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            return None
    if not isinstance(data, list) or len(data) != n:
        return None
    out = []
    for a in data:
        out.append({
            "sentiment": str(a.get("sentiment", "neutral")).lower().strip(),
            "theme": str(a.get("theme", "other")).lower().strip(),
            "feature": str(a.get("feature", "general")).strip(),
            "severity": str(a.get("severity", "medium")).lower().strip(),
            "summary": str(a.get("summary", "")).strip(),
        })
    return out


# ------------------------------------------------- deterministic fallback
_KEYWORDS = [
    ("search", ["search"]),
    ("checkout_payments", ["checkout", "upi", "payment", "pay"]),
    ("dashboard_performance", ["dashboard", "loading", "slow", "sluggish"]),
    ("pricing", ["pric", "charged", "billing", "premium"]),
    ("login_otp", ["otp", "login", "biometric", "session"]),
    ("notifications", ["notification"]),
    ("ui_design", ["design", "ui", "dark mode", "look"]),
    ("support_experience", ["support", "ticket", "agent"]),
]


def heuristic(item):
    """Keyword + rating based analysis. Used only if the LLM is unreachable."""
    text = item["feedback"].lower()
    theme = "other"
    for t, kws in _KEYWORDS:
        if any(k in text for k in kws):
            theme = t
            break
    try:
        rating = int(item.get("rating") or 3)
    except ValueError:
        rating = 3
    sentiment = "positive" if rating >= 4 else ("negative" if rating <= 2 else "neutral")
    severity = "high" if rating <= 1 else ("medium" if rating <= 3 else "low")
    return {"sentiment": sentiment, "theme": theme, "feature": theme,
            "severity": severity, "summary": item["feedback"][:80]}


# ------------------------------------------------------------- public API
def classify_batch(items, retries=1):
    """items: list of feedback dicts (need key 'feedback').
    Returns list of analysis dicts, same order, same length. Never raises."""
    numbered = "\n".join(f"{i + 1}. {it['feedback']}" for i, it in enumerate(items))
    user_msg = f"Classify these {len(items)} items:\n{numbered}"
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    use_json_mode = True
    last_err = None

    for _attempt in range(retries + 1):
        try:
            kwargs = dict(model=pick_model(), messages=messages, temperature=0.0)
            if use_json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = client().chat.completions.create(**kwargs)
            raw = resp.choices[0].message.content
            analyses = _parse_results(raw, len(items))
            if analyses is not None:
                return analyses
            last_err = ValueError(f"unparseable reply: {raw[:120]!r}")
        except Exception as e:                       # network/rate/JSON-mode errors
            last_err = e
            if "json" in str(e).lower() or "response_format" in str(e).lower():
                use_json_mode = False                # server rejected JSON mode
                messages[1]["content"] = user_msg + "\n(Reply with ONLY the JSON object, no prose.)"

    print(f"  ! LLM classification failed ({last_err}) -> heuristic fallback")
    return [heuristic(it) for it in items]