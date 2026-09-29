"""
FeedbackMind — analyst agent (core/analyst.py)
Question -> Hindsight recall -> Groq synthesizes a CITED answer.
Also: answer_no_memory() = the 'before' side of the before/after demo.

Quick terminal test:
    python -m core.analyst "Has dashboard performance improved after the v2.4 release?"
"""
import sys

from . import llm, memory

ANSWER_SYSTEM = (
    "You are FeedbackMind, a product-feedback analyst agent for the fintech "
    "app 'Finly'. Answer the product manager's question USING ONLY the numbered "
    "evidence memories provided. Cite evidence as [1], [2]... where you use it. "
    "Mention dates and channels when the evidence does. If the evidence is "
    "insufficient, say exactly what is missing. Be concise: 3-6 sentences; add a "
    "one-line 'Recommendation:' only if the question asks for action."
)

NO_MEMORY_SYSTEM = (
    "You are a product analyst for the fintech app 'Finly'. You have NO access "
    "to any feedback data or memory. Answer briefly and honestly state that you "
    "are guessing without data."
)


def gather_evidence(question, budget="high", max_items=12):
    """Hindsight's 4-arm search (semantic+keyword+graph+temporal) -> top memories."""
    res = memory.recall(question, budget=budget)
    return [r.text for r in res.results[:max_items]]


def answer(question):
    """The memory-powered answer, with citations."""
    evidence = gather_evidence(question)
    if not evidence:
        return {"answer": "I have no memories relevant to that question yet.",
                "evidence": []}
    numbered = "\n".join(f"[{i + 1}] {t}" for i, t in enumerate(evidence))
    resp = llm.client().chat.completions.create(
        model=llm.pick_model(),
        temperature=0.2,
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user",
             "content": f"Evidence memories:\n{numbered}\n\nQuestion: {question}"},
        ],
    )
    return {"answer": resp.choices[0].message.content, "evidence": evidence}


def answer_no_memory(question):
    """Same LLM, zero memory — for the before/after comparison."""
    resp = llm.client().chat.completions.create(
        model=llm.pick_model(),
        temperature=0.2,
        messages=[
            {"role": "system", "content": NO_MEMORY_SYSTEM},
            {"role": "user", "content": question},
        ],
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What are customers complaining about most?"
    try:
        out = answer(q)
        print("ANSWER:\n", out["answer"])
        print("\nEVIDENCE USED:")
        for i, e in enumerate(out["evidence"], 1):
            print(f"  [{i}] {e[:160]}")
    finally:
        memory.client().close()