"""
FeedbackMind — Streamlit dashboard (app.py)
Run:  streamlit run app.py
Tabs: Dashboard | Ask the Analyst | Digests | Memory Explorer | Before/After
"""
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from core import analyst, digest, llm, memory

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

st.set_page_config(page_title="FeedbackMind", page_icon="🧠", layout="wide")


# ------------------------------------------------------------ data loading
@st.cache_data(ttl=120, show_spinner=False)
def memory_rows():
    """Flatten Hindsight memories into plain dicts (cacheable, UI-friendly)."""
    rows = []
    for m in memory.all_memories(limit=1000):
        md = getattr(m, "metadata", None) or {}
        if not isinstance(md, dict):
            md = dict(md)
        text = getattr(m, "text", None) or getattr(m, "content", None) or ""
        ts = getattr(m, "timestamp", None) or getattr(m, "created_at", None) or ""
        rows.append({
            "date": str(ts)[:10],
            "type": getattr(m, "type", None) or md.get("type", "world"),
            "theme": md.get("theme", ""),
            "sentiment": md.get("sentiment", ""),
            "channel": md.get("channel", ""),
            "week": md.get("week", ""),
            "text": text,
        })
    return rows


@st.cache_data(ttl=120, show_spinner=False)
def csv_fallback_rows():
    """Only used if the server hides metadata: recompute stats from source CSV."""
    import csv as _csv
    path = DATA / "feedback.csv"
    if not path.exists():
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            an = llm.heuristic(r)
            rows.append({
                "date": r["date"], "type": "world", "theme": an["theme"],
                "sentiment": an["sentiment"], "channel": r["channel"],
                "week": str(memory.week_of(datetime.fromisoformat(r["date"]))),
                "text": r["feedback"],
            })
    return rows


def feedback_rows():
    rows = [r for r in memory_rows() if r["theme"]]      # feedback = has a theme
    if len(rows) < 10:                                    # metadata hidden?
        rows = csv_fallback_rows()
        if rows:
            st.caption("ℹ️ Memory metadata not exposed by this server build — "
                       "stats computed from source CSV instead.")
    return rows


def emerging_from(wt):
    alerts = []
    for theme, wk in wt.items():
        early = sum(wk.get(w, 0) for w in (1, 2, 3, 4))
        late = sum(wk.get(w, 0) for w in (5, 6, 7, 8))
        g = late / max(early, 1)
        if late >= 12 and g >= 1.8:
            alerts.append({"theme": theme, "early": early, "late": late,
                           "growth": round(g, 2),
                           "per_week": [wk.get(w, 0) for w in range(1, 9)]})
    return sorted(alerts, key=lambda a: a["growth"], reverse=True)



def tab_ingest():
    st.subheader("📥 Ingest new feedback — the agent learns instantly")
    st.caption("Any CSV with columns: date, channel, customer_id, customer_name, feedback, rating. "
               "No retraining, no restart: retained memories are answerable immediately.")
    up = st.file_uploader("Upload feedback CSV", type=["csv"])
    if up is not None:
        import csv as _csv
        import io
        rows = list(_csv.DictReader(io.StringIO(up.getvalue().decode("utf-8"))))
        if not rows or not {"date", "channel", "feedback"} <= set(rows[0].keys()):
            st.error("CSV must have at least: date, channel, feedback")
            return
        good, bad = [], 0
        for r in rows:
            try:
                datetime.fromisoformat(r["date"])
                good.append(r)
            except (ValueError, KeyError):
                bad += 1
        if bad:
            st.warning(f"Skipped {bad} row(s) with unparseable dates (need YYYY-MM-DD).")
        if st.button(f"Learn these {len(good)} feedback items", type="primary"):
            prog = st.progress(0.0, text="Classifying + retaining...")
            stats = Counter()
            for i in range(0, len(good), 8):
                batch = good[i:i + 8]
                for b in batch:
                    b.setdefault("customer_id", "user_upload")
                    b.setdefault("customer_name", "Uploaded user")
                    b.setdefault("rating", "")
                analyses = llm.classify_batch(batch)
                for item, an in zip(batch, analyses):
                    memory.store_feedback(item, an)
                    stats[an["theme"]] += 1
                prog.progress(min((i + 8) / len(good), 1.0),
                              text=f"{min(i + 8, len(good))}/{len(good)} learned")
            st.success(f"✅ Learned {len(good)} new items. Themes: {dict(stats)}")
            st.cache_data.clear()
            st.balloons()
            st.caption("Switch to 💬 Ask the Analyst — it already knows the new data.")

# ------------------------------------------------------------ tabs
def tab_dashboard():
    fb = feedback_rows()
    wt = defaultdict(Counter)
    ws = defaultdict(Counter)
    for r in fb:
        w = int(r["week"]) if r["week"] else 0
        wt[r["theme"]][w] += 1
        ws[r["sentiment"]][w] += 1

    pos = sum(1 for r in fb if r["sentiment"] == "positive")
    neg = sum(1 for r in fb if r["sentiment"] == "negative")
    alerts = emerging_from(wt)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Feedback memories", len(fb))
    c2.metric("Positive", f"{round(100 * pos / max(len(fb), 1))}%")
    c3.metric("Negative", f"{round(100 * neg / max(len(fb), 1))}%")
    c4.metric("🔴 Emerging issues", len(alerts))

    weeks = list(range(1, 9))
    sent_df = pd.DataFrame({
        "positive": [ws["positive"].get(w, 0) for w in weeks],
        "negative": [ws["negative"].get(w, 0) for w in weeks],
    }, index=[f"w{w}" for w in weeks])
    themes = Counter({t: sum(wk.values()) for t, wk in wt.items()})
    theme_df = pd.DataFrame(
        {"mentions": [themes[t] for t in themes]},
        index=list(themes),
    ).sort_values("mentions", ascending=False).head(8)

    lc, bc = st.columns(2)
    lc.subheader("Sentiment over time")
    lc.line_chart(sent_df)
    bc.subheader("Top themes")
    bc.bar_chart(theme_df)

    st.subheader("🔴 Emerging issues (detected from memory)")
    if alerts:
        for a in alerts:
            st.error(f"**{a['theme']}** — mentions grew {a['early']} → {a['late']} "
                     f"({a['growth']}×) · per week: {a['per_week']}")
    else:
        st.info("No accelerating themes right now.")

    rel = json.loads((DATA / "releases.json").read_text(encoding="utf-8"))
    st.caption("Product releases: " + " · ".join(
        f"v{r['version']} {r['title']} ({r['date']})" for r in rel))


def tab_ask():
    st.subheader("💬 Ask the Analyst (answers cite their memories)")
    suggestions = [
        "Has dashboard performance improved after the v2.4 release?",
        "What should the product team investigate next?",
        "Which customer complained about checkout across multiple channels?",
    ]
    for q in suggestions:
        if st.button(q, key=f"sug_{hash(q) % 99999}"):
            st.session_state["ask_q"] = q
    q = st.text_input("Your question", value=st.session_state.get("ask_q", ""))
    if st.button("Ask", type="primary") and q:
        with st.spinner("Recalling memories + synthesizing..."):
            out = analyst.answer(q)
        st.markdown(out["answer"])
        with st.expander(f"Evidence from memory ({len(out['evidence'])} memories)"):
            for i, e in enumerate(out["evidence"], 1):
                st.markdown(f"**[{i}]** {e}")


def tab_digests():
    st.subheader("📰 Weekly Digests — the learning loop, visible")
    path = DATA / "digests.json"
    digests = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not digests:
        st.info("No digests yet. Run `python -m core.digest seed` in the terminal, "
                "or generate one below.")
    else:
        latest = max(digests, key=int)
        for w in sorted(digests, key=int):
            d = digests[w]
            label = (f"Week {w} — from {d['week_start']} · "
                     f"{d['pm_instructions_applied']} PM instruction(s) applied")
            with st.expander(label, expanded=(w == latest)):
                st.markdown(d["text"])
    st.divider()
    st.subheader("🎓 Teach the agent")
    cw = st.number_input("Correction about week", 1, 8, 2)
    comment = st.text_area("PM correction / preference",
                           placeholder="e.g. Always mention churn risk for enterprise users.")
    if st.button("Record correction (retained as experience fact)") and comment:
        st.success(digest.record_pm_feedback(int(cw), comment))
    gw = st.number_input("Generate digest for week", 1, 8, 6, key="genweek")
    if st.button("Generate digest", type="primary"):
        with st.spinner("reflect() over the week's memories..."):
            st.markdown(digest.generate_digest(int(gw)))
        st.cache_data.clear()


def tab_memory():
    st.subheader("🧠 Memory Explorer — what Hindsight actually stored")
    rows = memory_rows()
    if not rows:
        st.warning("No memories found. Run the ingest first.")
        return
    c1, c2 = st.columns(2)
    kind = c1.selectbox("Show", ["Everything", "Feedback facts", "Releases",
                                 "Digests (experience)", "PM corrections"])
    search = c2.text_input("Search inside memories")
    view = rows
    if kind == "Feedback facts":
        view = [r for r in view if r["theme"]]
    elif kind == "Releases":
        view = [r for r in view if r["text"].startswith("PRODUCT RELEASE")]
    elif kind == "Digests (experience)":
        view = [r for r in view if "weekly digest" in r["text"].lower()]
    elif kind == "PM corrections":
        view = [r for r in view if "PM feedback" in r["text"]]
    if search:
        view = [r for r in view if search.lower() in r["text"].lower()]
    st.caption(f"{len(view)} memories (of {len(rows)} total in bank '{memory.BANK}')")
    if view:
        st.dataframe(
            pd.DataFrame(view)[["date", "type", "theme", "sentiment", "channel", "text"]],
            height=440, hide_index=True,
            column_config={"text": st.column_config.TextColumn("memory", width="large")},
        )


def tab_before_after():
    st.subheader("⚖️ Same question — plain LLM vs FeedbackMind")
    q = st.text_input("Question",
                      "Has dashboard performance improved after the v2.4 release?",
                      key="ba_q")
    if st.button("Run comparison", type="primary"):
        with st.spinner("Asking both versions..."):
            plain = analyst.answer_no_memory(q)
            smart = analyst.answer(q)
        c1, c2 = st.columns(2)
        c1.markdown("**🧠❌ Plain LLM (no memory)**")
        c1.warning(plain)
        c2.markdown("**🧠✅ FeedbackMind (Hindsight memory)**")
        c2.success(smart["answer"])
        with c2.expander(f"Citations ({len(smart['evidence'])} memories)"):
            for i, e in enumerate(smart["evidence"], 1):
                c2.markdown(f"**[{i}]** {e[:220]}")


# ------------------------------------------------------------ main
st.title("🧠 FeedbackMind")
st.caption("AI product-feedback agent with persistent memory — Hindsight + Groq")

with st.sidebar:
    st.header("State")
    st.write(f"Memory bank: `{memory.BANK}`")
    st.write(f"Memories loaded: {len(memory_rows())}")
    if st.button("🔄 Refresh from memory"):
        st.cache_data.clear()
        st.rerun()
t0, t1, t2, t3, t4, t5 = st.tabs(
    ["📥 Ingest CSV", "📊 Dashboard", "💬 Ask the Analyst",
     "📰 Digests", "🧠 Memory Explorer", "⚖️ Before/After"])
with t0:
    tab_ingest()
with t1:
    tab_dashboard()
with t2:
    tab_ask()
with t3:
    tab_digests()
with t4:
    tab_memory()
with t5:
    tab_before_after()